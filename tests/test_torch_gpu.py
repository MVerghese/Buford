"""Verify PyTorch runs and can execute on a CUDA GPU."""

import pytest
import torch


def test_torch_runs_on_gpu() -> None:
    if not torch.cuda.is_available():
        pytest.fail(
            "CUDA is not available — install a CUDA-enabled PyTorch build and working GPU drivers"
        )
    if torch.version.cuda is None:
        pytest.fail("PyTorch was built without CUDA")

    try:
        x = torch.tensor([1.0, 2.0, 3.0], device="cuda")
        assert x.sum().item() == 6.0
        y = torch.randn(32, 32, device="cuda")
        z = y @ y.T
    except torch.AcceleratorError as exc:
        pytest.fail(
            f"CUDA is visible but no GPU kernel could run ({exc}). "
            "Jetson Orin (sm_87) needs NVIDIA's Jetson PyTorch wheel; "
            "the standard PyTorch cu12 wheel does not include kernels for this GPU."
        )

    assert z.device.type == "cuda"
    assert torch.cuda.current_device() >= 0
