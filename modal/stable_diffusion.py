# ---
# output-directory: "/tmp/stable-diffusion-xl"
# args: ["--prompt", "An astronaut riding a green horse"]
# runtimes: ["runc", "gvisor"]
# ---
# # Stable Diffusion XL 1.0
#
# This example is similar to the [Stable Diffusion CLI](/docs/examples/stable_diffusion_cli)
# example, but it generates images from the larger SDXL 1.0 model. Specifically, it runs the
# first set of steps with the base model, followed by the refiner model.
#
# [Try out the live demo here!](https://modal-labs--stable-diffusion-xl-app.modal.run/) The first
# generation may include a cold-start, which takes around 20 seconds. The inference speed depends on the GPU
# and step count (for reference, an A100 runs 40 steps in 8 seconds).

# ## Basic setup

import io
from pathlib import Path
from typing import Dict

from modal import (
    Image,
    Mount,
    Stub,
    asgi_app,
    build,
    enter,
    gpu,
    method,
    web_endpoint,
    Secret
)

# ## Define a container image
#
# To take advantage of Modal's blazing fast cold-start times, we'll need to download our model weights
# inside our container image with a download function. We ignore binaries, ONNX weights and 32-bit weights.
#
# Tip: avoid using global variables in this function to ensure the download step detects model changes and
# triggers a rebuild.


sdxl_image = (
    Image.debian_slim(python_version="3.10")
    .apt_install(
        "libglib2.0-0", "libsm6", "libxrender1", "libxext6", "ffmpeg", "libgl1"
    )
    .pip_install(
        "diffusers==0.26.3",
        "invisible_watermark==0.2.0",
        "transformers~=4.38.2",
        "accelerate==0.27.2",
        "safetensors==0.4.2",
        "boto3"
    )
)

stub = Stub("stable-diffusion-xl")

with sdxl_image.imports():
    import torch
    from diffusers import DiffusionPipeline
    from fastapi import Response
    from huggingface_hub import snapshot_download

# ## Load model and run inference
#
# The container lifecycle [`@enter` decorator](https://modal.com/docs/guide/lifecycle-functions#container-lifecycle-beta)
# loads the model at startup. Then, we evaluate it in the `run_inference` function.
#
# To avoid excessive cold-starts, we set the idle timeout to 240 seconds, meaning once a GPU has loaded the model it will stay
# online for 4 minutes before spinning down. This can be adjusted for cost/experience trade-offs.


@stub.cls(gpu=gpu.H100(), container_idle_timeout=240, image=sdxl_image)
class Model:
    @build()
    def build(self):
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

    @enter()
    def enter(self):
        load_options = dict(
            torch_dtype=torch.float16,
            use_safetensors=True,
            variant="fp16",
            device_map="auto",
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

        # Compiling the model graph is JIT so this will increase inference time for the first run
        # but speed up subsequent runs. Uncomment to enable.
        # self.base.unet = torch.compile(self.base.unet, mode="reduce-overhead", fullgraph=True)
        # self.refiner.unet = torch.compile(self.refiner.unet, mode="reduce-overhead", fullgraph=True)

    def _inference(self, prompt, n_steps=24, high_noise_frac=0.8):
        negative_prompt = "disfigured, ugly, deformed"
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
        image.save(byte_stream, format="JPEG")

        return byte_stream

    @method()
    def inference(self, prompt, n_steps=24, high_noise_frac=0.8):
        return self._inference(
            prompt, n_steps=n_steps, high_noise_frac=high_noise_frac
        ).getvalue()

    @web_endpoint()
    def web_inference(self, prompt, n_steps=24, high_noise_frac=0.8):
        return Response(
            content=self._inference(
                prompt, n_steps=n_steps, high_noise_frac=high_noise_frac
            ).getvalue(),
            media_type="image/jpeg",
        )


# And this is our entrypoint; where the CLI is invoked. Explore CLI options
# with: `modal run stable_diffusion_xl.py --prompt "An astronaut riding a green horse"`



@stub.function(image=sdxl_image, secrets=[Secret.from_name("my-aws-secret")])
@web_endpoint(method="POST")
def image_generation(prompt: Dict):
    image_bytes = Model().inference.remote(prompt['text'])
    # dir = Path("/tmp/stable-diffusion-xl")
    # if not dir.exists():
    #     dir.mkdir(exist_ok=True, parents=True)

    # Return a Response object with the image bytes and set the appropriate content type
    import boto3

    # Create an S3 client
    s3 = boto3.resource('s3')
    s2 = boto3.client('s3')
    def count_images_in_bucket(bucket):
        """Counts the number of objects in the specified S3 bucket."""
        paginator = s2.get_paginator('list_objects_v2')
        page_iterator = paginator.paginate(Bucket=bucket)
        
        count = 0
        for page in page_iterator:
            if 'Contents' in page:
                count += len(page['Contents'])
        return count
    
    # Specify the bucket namepyt
    bucket_name = 'imagegen10'
    image_count = count_images_in_bucket(bucket_name) 


    # Specify the S3 key (name) for the uploaded image
    s3_key = f'image{image_count + 1}.jpeg'

    # Upload the image bytes
    s3.Object(bucket_name, s3_key).put(Body=image_bytes, ContentType='image/jpeg', ACL='public-read')
    # s3.Bucket(bucket_name).put_object(Key=s3_key, Body=image_bytes})
    image_url = f"https://{bucket_name}.s3.amazonaws.com/{s3_key}"

    return {"url": image_url}