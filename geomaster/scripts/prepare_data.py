import click
import torch
import glob
from PIL import Image
import os
import shutil
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed
from gaustudio import datasets, models
from gaustudio.pipelines import initializers
from geomaster.systems.tsdf_fusion_pipeline import tsdf_fusion

def process_image(image_path, output_normal_dir, output_mask_dir, normal_predictor, mask_predictor):
    image_name = os.path.splitext(os.path.basename(image_path))[0]
    input_image = Image.open(image_path)
    
    output_normal_path = os.path.join(output_normal_dir, f"{image_name}.png")
    if not os.path.exists(output_normal_path) and normal_predictor is not None:
        normal_image = normal_predictor(input_image)
        normal_image.save(output_normal_path)
        
    output_mask_path = os.path.join(output_mask_dir, f"{image_name}.png")
    if not os.path.exists(output_mask_path) and mask_predictor is not None:
        mask = mask_predictor.infer_pil(input_image)
        mask = Image.fromarray(mask)
        mask.save(output_mask_path)

@click.command()
@click.option('--source_path', '-s', required=True, help='Path to the dataset')
@click.option('--images', '-i', default="images", help='Path to the images dir')
@click.option('--masks', '-m', default="mask", help='Path to the masks dir')
@click.option('--num_workers', '-w', default=4, help='Number of worker threads')
def main(source_path: str, images: str, masks: str, num_workers: int) -> None:
    torch.hub._validate_not_a_forked_repo = lambda a, b, c: True
    # mask_predictor = torch.hub.load("aim-uofa/GenPercept", "GenPercept_Segmentation", trust_repo=True)
    mask_predictor = None
    normal_predictor = torch.hub.load("Stable-X/StableNormal", "StableNormal_turbo", trust_repo=True)
    # normal_predictor = None
    
    output_normal_dir = os.path.join(source_path, "normals")
    output_mask_dir = os.path.join(source_path, masks)
    os.makedirs(output_normal_dir, exist_ok=True)
    os.makedirs(output_mask_dir, exist_ok=True)

    image_paths = glob.glob(os.path.join(source_path, images, "*.png")) + \
                  glob.glob(os.path.join(source_path, images, "*.jpg")) + \
                  glob.glob(os.path.join(source_path, images, "*.jpeg"))

    for image_path in tqdm(image_paths, desc="Processing images"):
        process_image(image_path, output_normal_dir, output_mask_dir, normal_predictor, mask_predictor)

    dataset = datasets.make({
        "name": "colmap", 
        "source_path": source_path, 
        "masks": masks, 
        "data_device": "cuda", 
        "w_mask": True
    })

    tsdf_fusion(dataset, source_path)

    # initializer = initializers.make({"name":"VisualHull",
    #                                  "radius_scale": 2.5,
    #                                  "resolution": 256})
    # pcd = models.make("general_pcd")
    # initializer(pcd, dataset)
    #
    # visual_hull_path = os.path.join(source_path, 'visual_hull.ply')
    # shutil.copy(os.path.join(initializer.ws_dir, 'visual_hull.ply'), visual_hull_path)
    #
    # highlight_start = "\033[1;32m"
    # highlight_end = "\033[0m"
    # highlighted_command = f"{highlight_start}gm-recon -s {source_path} -m {visual_hull_path}{highlight_end}"
    # print(f"Done. Run {highlighted_command} to get the final result.")

if __name__ == "__main__":
    main()