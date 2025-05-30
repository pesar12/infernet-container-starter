import io
from typing import Any

import torch
from diffusers import DiffusionPipeline
from huggingface_hub import snapshot_download


class StableDiffusionWorkflow:
    def __init__(
        self,
        *args: Any,
        **kwargs: Any,
    ):
        self.args: list[Any] = list(args)
        self.kwargs: dict[Any, Any] = kwargs

        self.is_setup = False

    def setup(self) -> Any:
        ignore = [
            "*.bin",
            "*.onnx_data",
            "*/diffusion_pytorch_model.safetensors",
        ]
        snapshot_download(
            "stabilityai/stable-diffusion-xl-base-1.0", ignore_patterns=ignore
        )
        snapshot_download(
            "stabilityai/stable-diffusion-xl-refiner-1.0",
            ignore_patterns=ignore,
        )

        load_options = dict(
            torch_dtype=torch.float16,
            use_safetensors=True,
            variant="fp16",
        )

        # Load base model
        self.base = DiffusionPipeline.from_pretrained(
            "stabilityai/stable-diffusion-xl-base-1.0", **load_options
        )

        # Load refiner model
        self.refiner = DiffusionPipeline.from_pretrained(
            "stabilityai/stable-diffusion-xl-refiner-1.0",
            text_encoder_2=self.base.text_encoder_2,
            vae=self.base.vae,
            **load_options,
        )

        self.is_setup = True

    def inference(self, input: dict[str, Any]) -> bytes:
        negative_prompt = input.get("negative_prompt", "disfigured, ugly, deformed")
        prompt = input["prompt"]
        n_steps = input.get("n_steps", 24)
        high_noise_frac = input.get("high_noise_frac", 0.8)

        image = self.base(
            prompt=prompt,
            negative_prompt=negative_prompt,
            num_inference_steps=n_steps,
            denoising_end=high_noise_frac,
            output_type="latent",
        ).images

        image = self.refiner(
            prompt=prompt,
            negative_prompt=negative_prompt,
            num_inference_steps=n_steps,
            denoising_start=high_noise_frac,
            image=image,
        ).images[0]

        byte_stream = io.BytesIO()
        image.save(byte_stream, format="PNG")
        image_bytes = byte_stream.getvalue()

        return image_bytes
