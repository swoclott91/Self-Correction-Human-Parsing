#!/usr/bin/env python
# -*- encoding: utf-8 -*-

"""
@Author  :   Peike Li
@Contact :   peike.li@yahoo.com
@File    :   simple_extractor.py
@Time    :   8/30/19 8:59 PM
@Desc    :   Simple Extractor
@License :   This source code is licensed under the license found in the
             LICENSE file in the root directory of this source tree.
"""

import os
import torch
import argparse
import numpy as np
from PIL import Image
from tqdm import tqdm
import cv2

from torch.utils.data import DataLoader, Dataset
import torchvision.transforms as transforms

from .networks import init_model
from .transforms import transform_logits

# Add webp to the list of supported image extensions
IMG_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.ppm', '.bmp', '.pgm', '.tif', '.webp']

# Add this after the imports and before the classes
dataset_settings = {
    'lip': {
        'input_size': [473, 473],
        'num_classes': 20,
        'label': ['Background', 'Hat', 'Hair', 'Glove', 'Sunglasses', 'Upper-clothes', 'Dress', 'Coat',
                  'Socks', 'Pants', 'Jumpsuits', 'Scarf', 'Skirt', 'Face', 'Left-arm', 'Right-arm',
                  'Left-leg', 'Right-leg', 'Left-shoe', 'Right-shoe']
    },
    'atr': {
        'input_size': [512, 512],
        'num_classes': 18,
        'label': ['Background', 'Hat', 'Hair', 'Sunglasses', 'Upper-clothes', 'Skirt', 'Pants', 
                 'Dress', 'Belt', 'Left-shoe', 'Right-shoe', 'Face', 'Left-leg', 'Right-leg', 
                 'Left-arm', 'Right-arm', 'Bag', 'Scarf']
    },
    'pascal': {
        'input_size': [512, 512],
        'num_classes': 7,
        'label': ['Background', 'Head', 'Torso', 'Upper Arms', 'Lower Arms', 'Upper Legs', 'Lower Legs']
    }
}

def is_image_file(filename):
    """Check if a file is an image based on its extension."""
    return any(filename.lower().endswith(extension) for extension in IMG_EXTENSIONS)

class SimpleFolderDataset(Dataset):
    def __init__(self, root, input_size=[512, 512], transform=None):
        self.root = root
        self.input_size = input_size
        self.transform = transform
        self.images = []
        
        # List all image files
        for filename in os.listdir(root):
            if is_image_file(filename):
                self.images.append(filename)

    def __len__(self):
        return len(self.images)

    def __getitem__(self, index):
        img_path = os.path.join(self.root, self.images[index])
        img = Image.open(img_path).convert('RGB')  # Convert to RGB to ensure compatibility
        
        # Original image size
        width, height = img.size
        
        # Get center and scale
        center = np.array([width/2, height/2])
        scale = np.array([width, height])

        # Apply transform if specified
        if self.transform is not None:
            img = self.transform(img)

        meta = {
            'name': self.images[index],
            'center': center,
            'scale': scale,
            'width': width,
            'height': height
        }

        return img, meta

class GarmentParser:
    def __init__(self, model_path: str, dataset: str = 'atr', verbose: bool = False):
        """Initialize garment parser
        
        Args:
            model_path: Path to model weights
            dataset: Dataset used for training ('atr' or 'lip')
            verbose: Whether to print debug information
        """
        self.verbose = verbose
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        
        # Load dataset settings
        self.settings = dataset_settings[dataset]
        
        # Setup transform
        self.transform = transforms.Compose([
            transforms.Resize(self.settings['input_size']),
            transforms.ToTensor(),
            transforms.Normalize(
                mean=[0.406, 0.456, 0.485],
                std=[0.225, 0.224, 0.229]
            )
        ])
        
        # Initialize model with verbose setting
        self.model = init_model('resnet101', 
                               num_classes=self.settings['num_classes'],
                               pretrained=None)
        
        # Load weights and remove 'module.' prefix
        state_dict = torch.load(model_path)['state_dict']
        new_state_dict = {}
        for k, v in state_dict.items():
            name = k[7:] if k.startswith('module.') else k  # Remove 'module.' prefix
            new_state_dict[name] = v
        
        # Load cleaned state dict
        self.model.load_state_dict(new_state_dict)
        self.model.to(self.device)  # Move model to device
        
        # Set model to eval mode
        self.model.eval()
        
        # Disable gradients
        for param in self.model.parameters():
            param.requires_grad = False
        
        # Ensure all BN layers have verbose disabled
        for module in self.model.modules():
            if hasattr(module, 'verbose'):
                module.verbose = False

    def parse_image(self, image_path: str):
        """Parse image and return segmentation mask"""
        if self.verbose:
            print("\nTransform Debug:")
            # ... debug prints ...
        
        # Load and transform image
        img = Image.open(image_path).convert('RGB')
        img_np = np.array(img)
        orig_size = img.size  # (width, height)
        
        # Get image metadata
        width, height = img.size
        center = np.array([width/2, height/2])
        scale = np.array([width, height])
        
        # Transform and process
        img_tensor = self.transform(img).unsqueeze(0)
        
        with torch.no_grad():
            output = self.model(img_tensor.to(self.device))
            upsample = torch.nn.Upsample(size=self.settings['input_size'], 
                                       mode='bilinear', 
                                       align_corners=True)
            upsample_output = upsample(output[0][-1][0].unsqueeze(0))
            upsample_output = upsample_output.squeeze()
            upsample_output = upsample_output.permute(1, 2, 0)  # CHW -> HWC
            
            # Transform logits back to original image size
            logits_result = transform_logits(upsample_output.data.cpu().numpy(),
                                           center, scale, width, height,
                                           input_size=self.settings['input_size'])
            
            # Get parsing result and ensure correct orientation
            parsing_result = np.argmax(logits_result, axis=2)
            
            # Fix orientation - transpose if needed
            if parsing_result.shape[:2] != (height, width):
                print(f"Fixing mask orientation from {parsing_result.shape} to ({height}, {width})")
                if parsing_result.shape == (width, height):
                    parsing_result = parsing_result.T
                else:
                    # If dimensions don't match exactly, resize properly
                    parsing_result = cv2.resize(parsing_result.astype(np.float32), 
                                             (width, height),  # cv2.resize takes (width, height)
                                             interpolation=cv2.INTER_NEAREST)
            
            # Verify dimensions
            assert parsing_result.shape[:2] == (height, width), \
                f"Mask shape {parsing_result.shape[:2]} doesn't match image shape ({height}, {width})"
            
            # Debug output
            if self.verbose:
                print(f"\nDimension Debug:")
                print(f"Original image size: ({width}, {height})")
                print(f"Input tensor size: {img_tensor.shape}")
                print(f"Upsampled output size: {upsample_output.shape}")
                print(f"Logits result size: {logits_result.shape}")
                print(f"Final parsing result size: {parsing_result.shape}")
        
        return {
            'mask': parsing_result.astype(np.uint8),
            'classes': {name: idx for idx, name in enumerate(self.settings['label'])},
            'image_size': (height, width),
            'original_image': img_np
        }

    def get_garment_mask(self, parsing_result, garment_type='upper', category_path=None, exclude_arms=True):
        """Extract mask for specific garment type with category awareness
        
        Args:
            parsing_result: Result from parse_image
            garment_type: Default garment type if no category provided
            category_path: Shopify taxonomy path (e.g. "Apparel & Accessories > Clothing > One-Pieces")
            exclude_arms: Whether to exclude arms from mask
        """
        classes = parsing_result['classes']
        mask = parsing_result['mask']
        
        # Define regions to exclude
        exclude_indices = [
            classes['Background'],
            classes['Face'],
            classes['Hair'],
            classes['Belt'],
            classes['Scarf']
        ]
        
        if exclude_arms:
            exclude_indices.extend([classes['Left-arm'], classes['Right-arm']])
        
        # Handle category-based masking
        if category_path:
            categories = category_path.lower().split(' > ')
            
            # One-Pieces (Dresses, Jumpsuits, Rompers)
            if 'one-pieces' in categories:
                garment_indices = [classes['Dress']]
                # Don't exclude legs for jumpsuits/rompers
                exclude_indices = [i for i in exclude_indices 
                                 if i not in [classes['Left-leg'], classes['Right-leg']]]
                
            # Two-Pieces (Suits, Coordinates)
            elif 'suits' in categories or 'coordinates' in categories:
                garment_indices = [
                    classes['Upper-clothes'],
                    classes['Pants'],
                    classes['Skirt']
                ]
                
            # Tops
            elif 'tops' in categories:
                garment_indices = [classes['Upper-clothes']]
                
            # Bottoms
            elif 'bottoms' in categories or 'pants' in categories or 'skirts' in categories:
                garment_indices = [classes['Pants'], classes['Skirt']]
                exclude_arms = False  # Don't exclude arms for bottoms
                
            else:
                # Default to upper clothes if category not recognized
                garment_indices = [classes['Upper-clothes'], classes['Dress']]
        else:
            # Original behavior when no category provided
            if garment_type == 'dress':
                garment_indices = [classes['Dress']]
            elif garment_type == 'pants':
                garment_indices = [classes['Pants']]
                exclude_arms = False
            else:  # upper
                garment_indices = [classes['Upper-clothes'], classes['Dress']]
        
        # Create initial mask
        garment_mask = np.isin(mask, garment_indices).astype(np.uint8)
        exclude_mask = np.isin(mask, exclude_indices).astype(np.uint8)
        
        # Apply exclusions
        final_mask = garment_mask & ~exclude_mask
        
        if self.verbose:
            print("\nMask Statistics:")
            print(f"Image size: {mask.shape}")
            print(f"Initial mask coverage: {np.mean(garment_mask)*100:.1f}%")
            print(f"Final mask coverage: {np.mean(final_mask)*100:.1f}%")
            print(f"Number of components: {len(np.unique(final_mask))}")
        
        return final_mask

    def post_process_mask(self, mask, min_size=100):
        """Post-process the mask to remove noise and small components
        
        Args:
            mask: Binary mask array
            min_size: Minimum component size to keep
            
        Returns:
            Processed mask array
        """
        # Convert to binary
        binary_mask = (mask > 0).astype(np.uint8)
        
        # Find connected components
        num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(binary_mask)
        
        # Create new mask with only large enough components
        processed_mask = np.zeros_like(binary_mask)
        for i in range(1, num_labels):  # Skip background (0)
            if stats[i, cv2.CC_STAT_AREA] >= min_size:
                processed_mask[labels == i] = 255
            
        # Optional: Fill holes
        contours, _ = cv2.findContours(processed_mask, 
                                      cv2.RETR_EXTERNAL,
                                      cv2.CHAIN_APPROX_SIMPLE)
        
        for contour in contours:
            cv2.drawContours(processed_mask, [contour], -1, 255, -1)
        
        if self.verbose:
            print(f"Post-processing removed {num_labels-1} components")
            print(f"Remaining area: {np.sum(processed_mask > 0) / processed_mask.size * 100:.1f}%")
        
        return processed_mask

    def get_garment_mask_steps(self, result, garment_type='upper', category_path=None):
        """Get intermediate steps of garment mask generation"""
        mask = result['mask']
        
        # Get relevant classes based on category
        if category_path:
            selected_classes = self.get_category_classes(category_path)
        else:
            selected_classes = self.get_garment_classes(garment_type)
        
        # Create initial mask from selected classes
        initial_mask = np.zeros_like(mask)
        
        # Special handling for pants
        if category_path and 'pants' in category_path.lower():
            # Check coverage
            pants_coverage = np.sum(mask == self.settings['label'].index('Pants')) / mask.size
            dress_coverage = np.sum(mask == self.settings['label'].index('Dress')) / mask.size
            
            if pants_coverage < 0.05 and dress_coverage > 0.15:
                # If dress is detected but pants aren't, convert dress to pants
                dress_mask = mask == self.settings['label'].index('Dress')
                
                # Find the vertical center of the dress mask
                where_dress = np.where(dress_mask)
                if len(where_dress[0]) > 0:  # If we found any dress pixels
                    top_y = np.min(where_dress[0])
                    bottom_y = np.max(where_dress[0])
                    mid_y = (top_y + bottom_y) // 2
                    
                    # Take lower 60% of dress as pants
                    cutoff_y = int(top_y + (bottom_y - top_y) * 0.4)  # Start at 40% from top
                    initial_mask[cutoff_y:, :][dress_mask[cutoff_y:, :]] = 255
                    
                    if self.verbose:
                        print(f"\nDress to Pants Conversion:")
                        print(f"Dress vertical range: {top_y} to {bottom_y}")
                        print(f"Cutoff point: {cutoff_y} (40% from top)")
                else:
                    # Fallback to pants mask if no dress pixels found
                    initial_mask[mask == self.settings['label'].index('Pants')] = 255
            else:
                # Use pants mask normally
                initial_mask[mask == self.settings['label'].index('Pants')] = 255
                
                # Also include leg regions for better coverage
                leg_mask = (mask == self.settings['label'].index('Left-leg')) | \
                          (mask == self.settings['label'].index('Right-leg'))
                initial_mask[leg_mask] = 255
        else:
            # Normal processing for other categories
            for cls in selected_classes:
                initial_mask[mask == cls] = 255
        
        # Store debug info
        info = {
            'initial_mask': initial_mask.copy(),
            'selected_classes': selected_classes,
            'garment_type': garment_type,
            'category_path': category_path,
            'class_counts': {
                cls: np.sum(mask == cls) 
                for cls in selected_classes
            }
        }
        
        # Add coverage statistics
        info['class_coverage'] = {
            'dress': np.sum(mask == self.settings['label'].index('Dress')) / mask.size,
            'pants': np.sum(mask == self.settings['label'].index('Pants')) / mask.size,
            'legs': (np.sum(mask == self.settings['label'].index('Left-leg')) + 
                    np.sum(mask == self.settings['label'].index('Right-leg'))) / mask.size
        }
        
        # Apply post-processing
        final_mask = self.post_process_mask(initial_mask)
        info['final_mask'] = final_mask
        
        # Add post-processing stats
        info['post_processing'] = {
            'initial_coverage': np.sum(initial_mask > 0) / initial_mask.size * 100,
            'final_coverage': np.sum(final_mask > 0) / final_mask.size * 100,
        }
        
        return info

    def get_garment_classes(self, garment_type='upper'):
        """Get class indices for a given garment type
        
        Args:
            garment_type: Type of garment ('upper', 'lower', or 'full')
            
        Returns:
            List of class indices
        """
        classes = self.settings['label']
        class_indices = {name: idx for idx, name in enumerate(classes)}
        
        if garment_type == 'upper':
            return [
                class_indices['Upper-clothes'],
                class_indices['Dress']
            ]
        elif garment_type == 'lower':
            return [
                class_indices['Pants'],
                class_indices['Skirt']
            ]
        elif garment_type == 'full':
            return [
                class_indices['Upper-clothes'],
                class_indices['Dress'],
                class_indices['Pants'],
                class_indices['Skirt']
            ]
        else:
            raise ValueError(f"Unknown garment type: {garment_type}")

    def get_category_classes(self, category_path):
        """Get class indices based on Shopify category path"""
        classes = self.settings['label']
        class_indices = {name: idx for idx, name in enumerate(classes)}
        
        category_path = category_path.lower()
        categories = category_path.split(' > ')
        last_category = categories[-1]
        
        # Bottom wear - strict pants handling
        if any(x in last_category for x in ['pants', 'shorts']):
            # Only use pants class, ignore dress
            return [class_indices['Pants']]
        
        # Full body garments
        if any(x in last_category for x in [
            'one-pieces', 'dresses', 'jumpsuits', 'rompers',
            'wedding & bridal party dresses',
            'traditional & ceremonial clothing'
        ]):
            # Include both dress class and upper-clothes + pants combination
            return [
                class_indices['Dress'],
                class_indices['Upper-clothes'],
                class_indices['Pants']
            ]
        
        # Two piece sets
        elif any(x in last_category for x in [
            'suits', 'outfit sets', 'uniforms & workwear',
            'activewear', 'sleepwear & loungewear'
        ]):
            return [
                class_indices['Upper-clothes'],
                class_indices['Pants'],
                class_indices['Skirt']
            ]
        
        # Tops and upper body
        elif any(x in last_category for x in [
            'clothing tops', 'outerwear', 'lingerie',
            "men's undergarments", "girls' underwear",
            "boys' underwear"
        ]):
            return [class_indices['Upper-clothes']]
        
        # Bottom wear
        elif any(x in last_category for x in [
            'pants', 'shorts', 'skirts', 'skorts',
            'swimwear'  # Often bottom-focused
        ]):
            return [
                class_indices['Pants'],
                class_indices['Skirt']
            ]
        
        # Special cases
        elif 'maternity clothing' in last_category:
            # Include both full dress and separates for maternity
            return [
                class_indices['Dress'],
                class_indices['Upper-clothes'],
                class_indices['Pants'],
                class_indices['Skirt']
            ]
        
        elif 'baby & toddler clothing' in last_category:
            # Include all garment types for baby clothes
            return [
                class_indices['Dress'],
                class_indices['Upper-clothes'],
                class_indices['Pants']
            ]
        
        # Accessories and others (socks, etc)
        elif any(x in last_category for x in ['socks']):
            if self.verbose:
                print(f"Warning: Category '{last_category}' may not be suitable for garment parsing")
            return [class_indices['Socks']]
        
        # Default case
        else:
            if self.verbose:
                print(f"Warning: Unrecognized category '{category_path}', defaulting to upper clothes")
                print("Available classes:", list(class_indices.keys()))
            return [
                class_indices['Upper-clothes'],
                class_indices['Dress']
            ]

def get_arguments():
    """Parse all the arguments provided from the CLI.
    Returns:
      A list of parsed arguments.
    """
    parser = argparse.ArgumentParser(description="Self Correction for Human Parsing")

    parser.add_argument("--dataset", type=str, default='lip', choices=['lip', 'atr', 'pascal'])
    parser.add_argument("--model-restore", type=str, default='', help="restore pretrained model parameters.")
    parser.add_argument("--gpu", type=str, default='0', help="choose gpu device.")
    parser.add_argument("--input-dir", type=str, default='', help="path of input image folder.")
    parser.add_argument("--output-dir", type=str, default='', help="path of output image folder.")
    parser.add_argument("--logits", action='store_true', default=False, help="whether to save the logits.")

    return parser.parse_args()


def get_palette(num_cls):
    """ Returns the color map for visualizing the segmentation mask.
    Args:
        num_cls: Number of classes
    Returns:
        The color map
    """
    n = num_cls
    palette = [0] * (n * 3)
    for j in range(0, n):
        lab = j
        palette[j * 3 + 0] = 0
        palette[j * 3 + 1] = 0
        palette[j * 3 + 2] = 0
        i = 0
        while lab:
            palette[j * 3 + 0] |= (((lab >> 0) & 1) << (7 - i))
            palette[j * 3 + 1] |= (((lab >> 1) & 1) << (7 - i))
            palette[j * 3 + 2] |= (((lab >> 2) & 1) << (7 - i))
            i += 1
            lab >>= 3
    return palette


def main():
    args = get_arguments()

    gpus = [int(i) for i in args.gpu.split(',')]
    assert len(gpus) == 1
    if not args.gpu == 'None':
        os.environ["CUDA_VISIBLE_DEVICES"] = args.gpu

    num_classes = dataset_settings[args.dataset]['num_classes']
    input_size = dataset_settings[args.dataset]['input_size']
    label = dataset_settings[args.dataset]['label']
    print("Evaluating total class number {} with {}".format(num_classes, label))

    model = init_model('resnet101', num_classes=num_classes, pretrained=None)

    state_dict = torch.load(args.model_restore)['state_dict']
    from collections import OrderedDict
    new_state_dict = OrderedDict()
    for k, v in state_dict.items():
        name = k[7:]  # remove `module.`
        new_state_dict[name] = v
    model.load_state_dict(new_state_dict)
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    model.to(device)
    model.eval()

    transform = transforms.Compose([
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.406, 0.456, 0.485], std=[0.225, 0.224, 0.229])
    ])
    dataset = SimpleFolderDataset(root=args.input_dir, input_size=input_size, transform=transform)
    dataloader = DataLoader(dataset)

    if not os.path.exists(args.output_dir):
        os.makedirs(args.output_dir)

    palette = get_palette(num_classes)
    with torch.no_grad():
        for idx, batch in enumerate(tqdm(dataloader)):
            image, meta = batch
            img_name = meta['name'][0]
            c = meta['center'].numpy()[0]
            s = meta['scale'].numpy()[0]
            w = meta['width'].numpy()[0]
            h = meta['height'].numpy()[0]

            output = model(image.to(device))
            upsample = torch.nn.Upsample(size=input_size, mode='bilinear', align_corners=True)
            upsample_output = upsample(output[0][-1][0].unsqueeze(0))
            upsample_output = upsample_output.squeeze()
            upsample_output = upsample_output.permute(1, 2, 0)  # CHW -> HWC

            logits_result = transform_logits(upsample_output.data.cpu().numpy(), c, s, w, h, input_size=input_size)
            parsing_result = np.argmax(logits_result, axis=2)
            parsing_result_path = os.path.join(args.output_dir, img_name[:-4] + '.png')
            output_img = Image.fromarray(np.asarray(parsing_result, dtype=np.uint8))
            output_img.putpalette(palette)
            output_img.save(parsing_result_path)
            if args.logits:
                logits_result_path = os.path.join(args.output_dir, img_name[:-4] + '.npy')
                np.save(logits_result_path, logits_result)
    return


if __name__ == '__main__':
    main()
