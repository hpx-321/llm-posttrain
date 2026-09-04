#!/usr/bin/env python3
"""Offline DPO adapter built on veRL 0.7.1's TrainingWorker/FSDP Engine.

This follows veRL's official offline-DPO RFC (SPMD TrainingWorker, paired
preference data, reference-relative loss) while keeping version-specific
compatibility in the project layer.  No installed veRL files are modified.
"""

from __future__ import annotations

import math
import os
from functools import partial


def _positive_int(name: str) -> int:
    raw = os.environ[name]
    try:
        value = int(raw)
    except ValueError as exc:
        raise RuntimeError(f"{name} must be a positive integer, got: {raw}") from exc
    if value <= 0:
        raise RuntimeError(f"{name} must be a positive integer, got: {raw}")
    return value


def _nonnegative_int(name: str, default: int = 0) -> int:
    raw = os.environ.get(name, str(default))
    try:
        value = int(raw)
    except ValueError as exc:
        raise RuntimeError(f"{name} must be a non-negative integer, got: {raw}") from exc
    if value < 0:
        raise RuntimeError(f"{name} must be a non-negative integer, got: {raw}")
    return value


def _positive_float(name: str) -> float:
    raw = os.environ[name]
    try:
        value = float(raw)
    except ValueError as exc:
        raise RuntimeError(f"{name} must be a positive number, got: {raw}") from exc
    if not math.isfinite(value) or value <= 0:
        raise RuntimeError(f"{name} must be a positive finite number, got: {raw}")
    return value


def main() -> None:
    import torch
    from torch.utils.data import DistributedSampler
    from torchdata.stateful_dataloader import StatefulDataLoader

    from verl.trainer import sft_trainer
    from verl.utils import tensordict_utils as tu
    from verl.utils.dataset.dataset_utils import DatasetPadMode
    from verl.utils.device import get_device_name
    from verl.workers.engine_workers import TrainingWorker, TrainingWorkerConfig

    from frameworks.verl.create_my_card.rl.training.dpo_dataset import (
        DPOPairCollator,
        DPOPairDataset,
    )
    from frameworks.verl.create_my_card.rl.training.dpo_loss import (
        dpo_loss,
        sequence_completion_logps,
    )

    beta = _positive_float("DPO_BETA")
    max_prompt_length = _positive_int("DPO_MAX_PROMPT_LENGTH")
    repeat_train_to_size = _nonnegative_int("DPO_REPEAT_TRAIN_TO_SIZE")
    execution_mode = os.environ.get("PIPELINE_EXECUTION_MODE", "smoke")

    class DPOTrainingWorker(TrainingWorker):
        """Keep each flattened pair intact during veRL dynamic micro-batching.

        The upstream RFC uses a fat-packed item plus a newer engine expansion
        hook. veRL 0.7.1 already exposes ``force_group_size`` for the same
        pairing invariant, so the adapter can remain outside site-packages.
        """

        def train_batch(self, data):
            tu.assign_non_tensor(data, force_group_size=2)
            return super().train_batch(data)

        def infer_batch(self, data):
            tu.assign_non_tensor(
                data,
                force_group_size=2,
                global_batch_size=len(data) // 2 * self.engine.get_data_parallel_size(),
            )
            return super().infer_batch(data)

    class CreateMyCardDPOTrainer(sft_trainer.SFTTrainer):
        """SFTTrainer lifecycle with preference data, reference precompute and DPO loss."""

        def __init__(self, config):
            super().__init__(config)
            if self.resume_global_step != 0:
                raise RuntimeError(
                    "veRL DPO adapter reference precompute requires trainer.resume_mode=disable"
                )
            self._precompute_all_reference_logps()

        def _build_dataset(self):
            config = self.config
            tokenizer = self.model_config.tokenizer
            common = {
                "tokenizer": tokenizer,
                "max_length": int(config.data.max_length),
                "max_prompt_length": max_prompt_length,
            }
            self.train_dataset = DPOPairDataset(
                config.data.train_files,
                max_samples=int(config.data.get("train_max_samples", -1)),
                repeat_to_size=repeat_train_to_size,
                **common,
            )
            self.val_dataset = (
                DPOPairDataset(
                    config.data.val_files,
                    max_samples=int(config.data.get("val_max_samples", -1)),
                    **common,
                )
                if config.data.val_files
                else None
            )

        def _build_engine(self):
            config = TrainingWorkerConfig(
                model_type="language_model",
                model_config=self.model_config,
                engine_config=self.engine_config,
                optimizer_config=self.optimizer_config,
                checkpoint_config=self.checkpoint_config,
                profiler_config=self.profiler_config,
            )
            self.loss_fn = partial(dpo_loss, beta=beta)
            self.training_client = DPOTrainingWorker(config=config)
            self.training_client.set_loss_fn(loss_fn=self.loss_fn)
            self.engine = self.training_client.engine

        def _build_dataloader(self):
            dp_rank = self.engine.get_data_parallel_rank()
            dp_size = self.engine.get_data_parallel_size()
            self.global_batch_size = int(self.config.data.train_batch_size)
            if self.global_batch_size % dp_size:
                raise RuntimeError(
                    f"DPO global pair batch {self.global_batch_size} is not divisible by DP size {dp_size}"
                )
            self.train_batch_size_per_dp = self.global_batch_size // dp_size
            if len(self.train_dataset) < self.global_batch_size:
                raise RuntimeError(
                    f"DPO train set has {len(self.train_dataset)} pairs but one global batch "
                    f"requires {self.global_batch_size}; increase data or use smoke repeat"
                )
            self.collate_fn = DPOPairCollator()
            self.train_sampler = DistributedSampler(
                self.train_dataset,
                shuffle=True,
                num_replicas=dp_size,
                rank=dp_rank,
                drop_last=True,
            )
            self.train_dataloader = StatefulDataLoader(
                dataset=self.train_dataset,
                batch_size=self.train_batch_size_per_dp,
                sampler=self.train_sampler,
                collate_fn=self.collate_fn,
                num_workers=int(self.config.data.num_workers),
                pin_memory=False,
                drop_last=True,
            )
            if self.val_dataset is None:
                self.val_dataloader = None
                return
            self.val_sampler = DistributedSampler(
                self.val_dataset,
                shuffle=False,
                num_replicas=dp_size,
                rank=dp_rank,
                drop_last=False,
            )
            self.val_dataloader = StatefulDataLoader(
                dataset=self.val_dataset,
                batch_size=int(os.environ.get("DPO_PER_DEVICE_EVAL_BATCH_SIZE", "1")),
                sampler=self.val_sampler,
                collate_fn=self.collate_fn,
                num_workers=int(self.config.data.num_workers),
                pin_memory=False,
                drop_last=False,
            )

        def _reference_loader(self, dataset):
            sampler = DistributedSampler(
                dataset,
                shuffle=False,
                num_replicas=self.engine.get_data_parallel_size(),
                rank=self.engine.get_data_parallel_rank(),
                drop_last=False,
            )
            return StatefulDataLoader(
                dataset=dataset,
                batch_size=1,
                sampler=sampler,
                collate_fn=self.collate_fn,
                num_workers=0,
                pin_memory=False,
                drop_last=False,
            )

        def _precompute_reference_logps(self, dataset) -> None:
            local_values: dict[int, tuple[float, float]] = {}
            meta = {
                "use_remove_padding": self.config.model.use_remove_padding,
                "use_dynamic_bsz": True,
                "max_token_len_per_gpu": self.config.data.max_token_len_per_gpu,
                "micro_batch_size_per_gpu": 2,
                "temperature": 1.0,
                "global_batch_size": self.engine.get_data_parallel_size(),
                "pad_mode": DatasetPadMode.NO_PADDING,
                "pad_token_id": self.model_config.tokenizer.pad_token_id,
                "compute_loss": False,
            }
            for batch in self._reference_loader(dataset):
                data = tu.get_tensordict(tensor_dict=batch, non_tensor_dict=meta)
                output = self.training_client.infer_batch(data)
                if output is None:
                    raise RuntimeError("veRL DPO adapter reference forward returned no model output")
                sequence_logps = sequence_completion_logps(
                    output["log_probs"], batch["loss_mask"]
                )
                sample_indices = batch["pair_index"].tolist()
                selected = batch["is_chosen"].tolist()
                by_pair: dict[int, dict[bool, float]] = {}
                for index, is_chosen_value, logp in zip(
                    sample_indices, selected, sequence_logps.tolist(), strict=True
                ):
                    by_pair.setdefault(int(index), {})[bool(is_chosen_value)] = float(logp)
                for index, values in by_pair.items():
                    if set(values) != {False, True}:
                        raise RuntimeError(f"incomplete reference pair at index {index}")
                    local_values[index] = (values[True], values[False])

            values = torch.zeros((len(dataset), 2), dtype=torch.float32)
            counts = torch.zeros(len(dataset), dtype=torch.float32)
            for index, pair in local_values.items():
                values[index] = torch.tensor(pair, dtype=torch.float32)
                counts[index] = 1
            values = values.to(get_device_name())
            counts = counts.to(get_device_name())
            group = self.engine.get_data_parallel_group()
            torch.distributed.all_reduce(values, group=group)
            torch.distributed.all_reduce(counts, group=group)
            if torch.any(counts == 0):
                raise RuntimeError("distributed reference precompute missed DPO rows")
            values = (values / counts.unsqueeze(-1)).cpu()
            for index, pair in enumerate(values.tolist()):
                dataset.set_reference_logps(index, pair[0], pair[1])
            dataset.require_complete_reference()

        def _precompute_all_reference_logps(self) -> None:
            if self.rank == 0:
                print("Precomputing fixed DPO reference log-probs with the veRL FSDP policy engine")
            self._precompute_reference_logps(self.train_dataset)
            if self.val_dataset is not None:
                self._precompute_reference_logps(self.val_dataset)
            torch.distributed.barrier()

    if execution_mode == "smoke":
        def skip_checkpoint_save(handler, step):
            if getattr(handler, "rank", 0) == 0:
                print(f"DPO smoke: skipped checkpoint saving at step {step}")

        sft_trainer.CheckpointHandler.save_checkpoint = skip_checkpoint_save

    sft_trainer.SFTTrainer = CreateMyCardDPOTrainer
    sft_trainer.main()


if __name__ == "__main__":
    main()
