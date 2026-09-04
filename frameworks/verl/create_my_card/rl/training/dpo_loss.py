"""DPO objective independent from dataset loading and trainer orchestration.

The sigmoid objective and distributed micro-batch scaling follow veRL's
offline-DPO RFC.  Keeping them in this module makes the algorithm testable
without coupling it to the TaskSpec dataset or launcher.
"""

from __future__ import annotations

import torch
import torch.nn.functional as F


def sequence_completion_logps(
    token_logps: torch.Tensor, loss_mask: torch.Tensor
) -> torch.Tensor:
    """Sum next-token log-probs over completion tokens for every sequence."""
    logp_rows = token_logps.unbind() if token_logps.is_nested else token_logps.unbind(0)
    mask_rows = loss_mask.unbind() if loss_mask.is_nested else loss_mask.unbind(0)
    if len(logp_rows) != len(mask_rows):
        raise ValueError("token_logps and loss_mask batch sizes differ")
    values = []
    for logps, mask in zip(logp_rows, mask_rows, strict=True):
        if logps.numel() != mask.numel():
            raise ValueError("token_logps and loss_mask sequence lengths differ")
        values.append((logps[:-1] * mask[1:].to(logps.dtype)).sum())
    return torch.stack(values)


def _ordered_pair_values(
    values: torch.Tensor, pair_index: torch.Tensor, is_chosen: torch.Tensor
) -> tuple[torch.Tensor, torch.Tensor]:
    chosen_ids = pair_index[is_chosen]
    rejected_ids = pair_index[~is_chosen]
    chosen_order = torch.argsort(chosen_ids)
    rejected_order = torch.argsort(rejected_ids)
    if not torch.equal(chosen_ids[chosen_order], rejected_ids[rejected_order]):
        raise ValueError("each DPO micro-batch must contain one chosen and rejected sequence per pair")
    return values[is_chosen][chosen_order], values[~is_chosen][rejected_order]


def dpo_loss(*, beta: float, model_output, data, dp_group=None):
    """Compute the reference-relative sigmoid DPO loss for a veRL Engine batch."""
    del dp_group
    from verl.utils import tensordict_utils as tu

    policy_logps = sequence_completion_logps(model_output["log_probs"], data["loss_mask"])
    pair_index = data["pair_index"]
    is_chosen = data["is_chosen"]
    policy_chosen, policy_rejected = _ordered_pair_values(
        policy_logps, pair_index, is_chosen
    )
    reference_chosen, reference_rejected = _ordered_pair_values(
        data["reference_logps"], pair_index, is_chosen
    )
    logits = (policy_chosen - policy_rejected) - (
        reference_chosen - reference_rejected
    )
    losses = -F.logsigmoid(beta * logits)

    dp_size = int(tu.get_non_tensor_data(data, "dp_size", 1))
    global_pair_batch = int(
        tu.get_non_tensor_data(data, "global_batch_size", losses.numel() * dp_size)
    )
    if global_pair_batch <= 0:
        raise ValueError("global_batch_size must be positive")
    loss = losses.sum() * dp_size / global_pair_batch
    return loss, {}
