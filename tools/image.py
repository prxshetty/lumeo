"""Image generation tool using DALL-E."""
# todos : add image storing to the same file and to store images as well
import os
from typing import Optional
from openai import OpenAI
import chainlit as cl
from pydantic import BaseModel, Field
from utils.ai_models import get_llm, get_image_generation_config
from utils.common import logger, scratch_pad_dir
import aiohttp
import time


class EnhancedPrompt(BaseModel):
    """Class for the text prompt"""

    content: str = Field(
        ...,
        description="The enhanced text prompt to generate an image",
    )


class ImageGenerationParams(BaseModel):
    """Parameters for image generation"""
    size: str = Field(default="1024x1024")
    quality: str = Field(default="standard")
    style: str = Field(default="vivid")


generate_image_def = {
    "name": "generate_image",
    "description": "Generates an image based on a given prompt using DALL-E.",
    "parameters": {
        "type": "object",
        "properties": {
            "prompt": {
                "type": "string",
                "description": "The prompt to generate an image (e.g., 'A beautiful sunset over the mountains')",
            },
            "size": {
                "type": "string",
                "description": "Size of the image (1024x1024, 1024x1792, or 1792x1024)",
                "default": "1024x1024"
            },
            "quality": {
                "type": "string",
                "description": "Quality of the image (standard or hd)",
                "default": "standard"
            },
            "style": {
                "type": "string",
                "description": "Style of the image (vivid or natural)",
                "default": "vivid"
            }
        },
        "required": ["prompt"],
    },
}


async def enhance_prompt(prompt: str, llm) -> str:
    """Enhance the image generation prompt using LLM."""
    structured_llm = llm.with_structured_output(EnhancedPrompt)
    system_template = """
    Enhance the given prompt using best prompt engineering techniques for DALL-E 3.
    Add relevant details about style, lighting, and composition while maintaining the original intent.

    # Original Prompt
    {prompt}

    # Guidelines
    1. Be specific about visual details
    2. Include lighting and atmosphere
    3. Specify artistic style if relevant
    4. Maintain the core concept of the original prompt
    """
    
    return structured_llm.invoke(
        system_template.format(prompt=prompt)
    ).content


async def generate_image_handler(
    prompt: str,
    size: Optional[str] = None,
    quality: Optional[str] = None,
    style: Optional[str] = None
) -> str:
    """Generates an image based on a given prompt using DALL-E."""
    try:
        logger.info(f"✨ Processing image generation request for prompt: '{prompt}'")
        
        # Get configurations
        img_config = get_image_generation_config()
        
        # Use provided parameters or defaults from config
        params = ImageGenerationParams(
            size=size or img_config["default_size"],
            quality=quality or img_config["default_quality"],
            style=style or img_config["default_style"]
        )

        # Enhance prompt
        llm = get_llm("image_prompt")
        enhanced_prompt = await enhance_prompt(prompt, llm)
        logger.info(f"🌄 Enhanced prompt: '{enhanced_prompt}'")

        # Generate image
        client = OpenAI()
        response = client.images.generate(
            model=img_config["model"],
            prompt=enhanced_prompt,
            size=params.size,
            quality=params.quality,
            style=params.style,
            n=1
        )

        image_url = response.data[0].url
        image = cl.Image(url=image_url, name="Generated Image", display="inline")
        
        await cl.Message(
            content=f"Image generated with the prompt: '{enhanced_prompt}'",
            elements=[image],
        ).send()

        image_dir = os.path.join(scratch_pad_dir, "images")
        os.makedirs(image_dir, exist_ok=True)
        img_path = os.path.join(image_dir, f"image_{int(time.time())}.png")
        
        async with aiohttp.ClientSession() as session:
            async with session.get(image_url) as response:
                if response.status == 200:
                    with open(img_path, "wb") as f:
                        f.write(await response.read())
                    logger.info(f"💾 Image saved to {img_path}")

        return "Image successfully generated"

    except Exception as e:
        error_message = f"Error generating image: {str(e)}"
        logger.error(f"❌ {error_message}")
        await cl.Message(content=error_message, type="error").send()
        return {"error": error_message}


generate_image = (generate_image_def, generate_image_handler)
