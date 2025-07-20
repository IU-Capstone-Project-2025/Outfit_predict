# trained model - use default YOLOv8 model if custom model not available
import os
from typing import List, Tuple

import cv2
import matplotlib.pyplot as plt
import numpy as np
from app.ml.encoding_models import FashionClipEncoder
from PIL import Image as PILImage
from ultralytics import SAM, YOLO

try:
    if os.path.exists("app/ml/best.pt"):
        print("✅ Loading custom YOLO model")
        model = YOLO("app/ml/best.pt")
    else:
        print("⚠️ Custom YOLO model not found, using default YOLOv8n")
        model = YOLO("yolov8n.pt")  # Will download automatically
except Exception as e:
    print(f"❌ Error loading YOLO model: {e}")
    print("Using default YOLOv8n model")
    model = YOLO("yolov8n.pt")


def get_clothes_from_img(img_path):
    # read the image
    img = cv2.imread(img_path)
    # get the height and width for future calculations

    img_height, img_width, _ = img.shape
    names = {
        0: "sunglass",
        1: "hat",
        2: "jacket",
        3: "shirt",
        4: "pants",
        5: "shorts",
        6: "skirt",
        7: "dress",
        8: "bag",
        9: "shoe",
    }

    # predict the clothes
    results = model.predict(img_path)
    # get the boxes of clothes
    results_boxes = results[0].boxes
    label = []
    # write them in appropriate format so that we can iterate through them easily
    for cls, boxes in zip(results_boxes.cls, results_boxes.xywhn):
        to_add = [cls]
        to_add.extend(list(boxes))
        label.append(to_add)
    count_clothes = {}
    parts = []
    for obj in label:
        name, x, y, width, height = obj
        # get the coordinates from model prediction
        # since we get center coordinates and width and height
        # we need to calculate coordinates for the rectangle's  two corner points
        # calculations are somewhat intuitive and to check correctness
        # you can go and write on paper and check
        name = int(name.item())
        if name in count_clothes:
            count_clothes[name] += 1
            name = str(names[name]) + f"_{count_clothes[name] - 1}"
        else:
            count_clothes[name] = 1
            name = names[name] + "_0"
        x = float(x)
        y = float(y)
        width = float(width)
        height = float(height)
        x1_real = int(np.abs(x - (width / 2)) * img_width)
        x2_real = int(np.abs(x + (width / 2)) * img_width)
        y1_real = int(np.abs(y + (height / 2)) * img_height)
        y2_real = int(np.abs(y - (height / 2)) * img_height)
        parts.append((name, img[y2_real:y1_real, x1_real:x2_real]))
    return parts


class FashionSegmentationModel:
    """
    A comprehensive model for detecting and segmenting fashion items in images.
    Combines YOLOv8 for object detection and Segment Anything Model (SAM) for
    high-precision segmentation. Provides visualization utilities and standardized
    output generation.

    Attributes:
        detection_model (YOLO): Pretrained YOLOv8 detection model
        segmentation_model (SAM): Pretrained SAM segmentation model
        device (str): Computation device (e.g., 'cpu', 'cuda')

    Typical usage:
        model = FashionSegmentationModel("yolo.pt", "sam.pt", "cuda")
        segments = model.get_segment_images("fashion.jpg")
        model.visualize_segments("fashion.jpg")
    """

    def __init__(self, yolo_model_path: str, sam_model_path: str, device: str = ""):
        """
        Initialize detection and segmentation models.

        Args:
            yolo_model_path: Path to YOLOv8 .pt weights file
            sam_model_path: Path to SAM .pt weights file
            device: Hardware device for inference ('' for auto-detection)
        """
        try:
            if os.path.exists(yolo_model_path):
                file_size = os.path.getsize(yolo_model_path)
                print(
                    f"✅ Found custom YOLO model at {yolo_model_path} (size: {file_size} bytes)"
                )
                self.detection_model = YOLO(yolo_model_path)
            else:
                print(
                    f"⚠️ Warning: YOLO model not found at {yolo_model_path}, using default YOLOv8n"
                )
                self.detection_model = YOLO("yolov8n.pt")
        except Exception as e:
            print(f"❌ Error loading YOLO model: {e}")
            self.detection_model = YOLO("yolov8n.pt")

        try:
            if os.path.exists(sam_model_path):
                file_size = os.path.getsize(sam_model_path)
                print(
                    f"✅ Found custom SAM model at {sam_model_path} (size: {file_size} bytes)"
                )
                self.segmentation_model = SAM(sam_model_path)
            else:
                print(
                    f"⚠️ Warning: SAM model not found at {sam_model_path}, using default SAM"
                )
                self.segmentation_model = SAM("sam_b.pt")  # Will download automatically
        except Exception as e:
            print(f"❌ Error loading SAM model: {e}")
            self.segmentation_model = SAM("sam_b.pt")

        self.device = device

    def _detect_clothes(self, img_path: str) -> List[Tuple[str, List[int]]]:
        """
        Detect fashion items and return bounding box coordinates.

        Args:
            img_path: Path to input image

        Returns:
            List of tuples (class_name, [xmin, ymin, xmax, ymax])

        Raises:
            ValueError: If duplicate clothing classes are detected

        Process:
            1. Load image and get dimensions
            2. Run YOLO detection
            3. Convert center-based coordinates to corner coordinates
            4. Validate unique class detection
        """
        image = cv2.imread(img_path)
        img_height, img_width = image.shape[:2]

        # Clothing class mapping
        classes = {
            0: "sunglass",
            1: "hat",
            2: "jacket",
            3: "shirt",
            4: "pants",
            5: "shorts",
            6: "skirt",
            7: "dress",
            8: "bag",
            9: "shoe",
        }

        # Perform detection
        clothes = self.detection_model.predict(img_path)
        bounding_boxes = clothes[0].boxes.cpu().numpy()

        # Process detections
        cloth_labels = []
        for cloth_class, cloth_box in zip(bounding_boxes.cls, bounding_boxes.xywh):
            cloth_labels.append([cloth_class] + list(cloth_box))

        detected_clothes = []
        found_clothes = set()

        for label in cloth_labels:
            name, x, y, width, height = label
            name = int(name)

            # Skip 'bag' class due to obvious and numerous artefacts
            if name == 8:
                continue

            # Validate unique classes
            if name in found_clothes:
                raise ValueError(f"Duplicate {classes[name]} detected!")
            found_clothes.add(name)

            # Convert to corner coordinates
            name = classes[name]
            xmin = max(0, int(x - width / 2))
            xmax = min(img_width, int(x + width / 2))
            ymin = max(0, int(y - height / 2))
            ymax = min(img_height, int(y + height / 2))

            detected_clothes.append((name, [xmin, ymin, xmax, ymax]))

        return detected_clothes

    def segment_clothes(self, img_path: str) -> Tuple[List[np.ndarray], List[str]]:
        """
        Perform segmentation on detected fashion items.

        Args:
            img_path: Path to input image

        Returns:
            Tuple containing:
                - List of normalized segmentation polygons (xyn format)
                - List of clothing class names
        """
        detected_clothes = self._detect_clothes(img_path)
        if len(detected_clothes) == 0:
            return ([], [])
        bounding_boxes = [item[1] for item in detected_clothes]
        cloth_names = [item[0] for item in detected_clothes]

        # Run segmentation
        segmentation_result = self.segmentation_model.predict(
            img_path,
            bboxes=bounding_boxes,
            verbose=False,
            save=False,
            device=self.device,
        )

        # Extract normalized polygons
        segments = segmentation_result[0].masks.xyn
        return segments, cloth_names

    def visualize_bounding_boxes(self, img_path: str) -> None:
        """
        Visualize detected bounding boxes with cropped regions.

        Args:
            img_path: Path to input image

        Output:
            Grid plot (max 4 items) showing cropped regions with class labels
        """
        image = cv2.imread(img_path)
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        detected_clothes = self._detect_clothes(img_path)
        if len(detected_clothes) == 0:
            return None

        plt.figure(figsize=(15, 10))
        for i, cloth in enumerate(detected_clothes):
            name, (xmin, ymin, xmax, ymax) = cloth
            cropped = image[ymin:ymax, xmin:xmax]

            plt.subplot(2, 2, i + 1)
            plt.imshow(cropped)
            plt.axis("off")
            plt.title(f"{name}")

        plt.tight_layout()
        plt.show()

    def visualize_segments(self, img_path: str) -> None:
        """
        Comprehensive visualization of segmentation results.

        Three-panel visualization:
        1. Original image with bounding boxes and class labels
        2. Segmentation contours overlaid on original image
        3. Combined segmentation mask with color coding

        Args:
            img_path: Path to input image
        """
        segments, cloth_names = self.segment_clothes(img_path)
        if len(segments) == 0:
            return None
        image = cv2.imread(img_path)
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        original_h, original_w = image.shape[:2]

        # Create copy for contour drawing
        contour_image = image.copy()

        # Initialize figure
        plt.figure(figsize=(18, 10))

        # Panel 1: Bounding boxes
        plt.subplot(131)
        display_img = image.copy()
        detected_bboxes = [item[1] for item in self._detect_clothes(img_path)]

        for i, (name, bbox) in enumerate(zip(cloth_names, detected_bboxes)):
            xmin, ymin, xmax, ymax = bbox
            cv2.rectangle(display_img, (xmin, ymin), (xmax, ymax), (0, 255, 0), 2)
            cv2.putText(
                display_img,
                name,
                (xmin, ymin - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.9,
                (0, 255, 0),
                2,
            )

        plt.imshow(display_img)
        plt.title("Detected Objects")
        plt.axis("off")

        # Panel 2: Segmentation contours
        plt.subplot(132)
        for i, segment in enumerate(segments):
            # Validate segment data
            if segment is None or len(segment) == 0:
                continue

            # Convert normalized to absolute coordinates
            absolute_segment = segment.copy()

            # Check for invalid coordinates
            if np.any(np.isnan(absolute_segment)) or np.any(np.isinf(absolute_segment)):
                continue

            absolute_segment[:, 0] *= original_w
            absolute_segment[:, 1] *= original_h

            points = absolute_segment.reshape((-1, 1, 2)).astype(np.int32)

            # Validate points
            if len(points) < 3 or points.shape[1] != 1 or points.shape[2] != 2:
                continue

            # Clamp points to image boundaries
            points[:, 0, 0] = np.clip(points[:, 0, 0], 0, original_w - 1)
            points[:, 0, 1] = np.clip(points[:, 0, 1], 0, original_h - 1)

            try:
                # Draw contours
                cv2.polylines(
                    contour_image,
                    [points],
                    isClosed=True,
                    color=(0, 255, 0),
                    thickness=2,
                )

                # Add text labels at centroid
                M = cv2.moments(points)
                if M["m00"] != 0:
                    cX = int(M["m10"] / M["m00"])
                    cY = int(M["m01"] / M["m00"])
                    cv2.putText(
                        contour_image,
                        cloth_names[i],
                        (cX, cY),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        1,
                        (255, 0, 0),
                        2,
                    )
            except cv2.error as e:
                print(f"OpenCV contour drawing error: {e}. Skipping this segment.")
                continue

        plt.imshow(contour_image)
        plt.title("Segmentation Contours")
        plt.axis("off")

        # Panel 3: Combined mask
        plt.subplot(133)
        combined_mask = np.zeros((original_h, original_w), dtype=np.uint8)

        for i, segment in enumerate(segments):
            # Validate segment data
            if segment is None or len(segment) == 0:
                continue

            absolute_segment = segment.copy()

            # Check for invalid coordinates
            if np.any(np.isnan(absolute_segment)) or np.any(np.isinf(absolute_segment)):
                continue

            absolute_segment[:, 0] *= original_w
            absolute_segment[:, 1] *= original_h

            points = absolute_segment.reshape((-1, 1, 2)).astype(np.int32)

            # Validate points
            if len(points) < 3 or points.shape[1] != 1 or points.shape[2] != 2:
                continue

            # Clamp points to image boundaries
            points[:, 0, 0] = np.clip(points[:, 0, 0], 0, original_w - 1)
            points[:, 0, 1] = np.clip(points[:, 0, 1], 0, original_h - 1)

            mask = np.zeros((original_h, original_w), dtype=np.uint8)
            try:
                cv2.fillPoly(mask, [points], color=np.random.randint(0, 255))
                combined_mask = cv2.bitwise_or(combined_mask, mask)
            except cv2.error as e:
                print(
                    f"OpenCV fillPoly error in visualization: {e}. Skipping this segment."
                )
                continue

        plt.imshow(combined_mask, cmap="jet")
        plt.title("Combined Mask")
        plt.axis("off")

        plt.tight_layout()
        plt.show()

    def get_segment_images(
        self, img_path: str, target_size: int = 640
    ) -> Tuple[List[np.ndarray], List[str]]:
        """
        Generate standardized segment images.

        Output images feature:
        - Uniform size (target_size x target_size)
        - Centered clothing item
        - Item occupies ~80% of image area
        - Gray background (128, 128, 128)
        - Preserved aspect ratio

        Args:
            img_path: Path to source image
            target_size: Output image dimensions (default 640)

        Returns:
            Tuple containing:
                - List of RGB images (numpy arrays)
                - List of clothing class names

        Process:
            1. Extract segments and create masks
            2. Apply masks to original image
            3. Calculate bounding box with 10% padding
            4. Create RGBA image with transparency
            5. Resize with preserved aspect ratio
            6. Composite onto gray background
        """
        segments, cloth_names = self.segment_clothes(img_path)
        if len(segments) == 0:
            return ([], [])
        image = cv2.imread(img_path)
        h, w = image.shape[:2]

        segment_images = []
        bg_color = (128, 128, 128)  # Gray background

        for segment in segments:
            # Validate segment data
            if segment is None or len(segment) == 0:
                continue

            # Convert normalized coordinates to absolute
            absolute_segment = segment.copy()

            # Check for invalid coordinates (NaN, infinity)
            if np.any(np.isnan(absolute_segment)) or np.any(np.isinf(absolute_segment)):
                continue

            absolute_segment[:, 0] *= w
            absolute_segment[:, 1] *= h
            points = absolute_segment.reshape((-1, 1, 2)).astype(np.int32)

            # Enhanced validation for OpenCV fillPoly requirements
            if len(points) < 3:
                continue

            # Validate points shape and data
            if points.shape[1] != 1 or points.shape[2] != 2:
                continue

            # Check if points contain valid coordinate values
            if (
                np.any(points < 0)
                or np.any(points[:, 0, 0] >= w)
                or np.any(points[:, 0, 1] >= h)
            ):
                # Clamp points to image boundaries
                points[:, 0, 0] = np.clip(points[:, 0, 0], 0, w - 1)
                points[:, 0, 1] = np.clip(points[:, 0, 1], 0, h - 1)

            # Create binary mask
            mask = np.zeros((h, w), dtype=np.uint8)
            try:
                cv2.fillPoly(mask, [points], 255)
            except cv2.error as e:
                print(f"OpenCV fillPoly error: {e}. Skipping this segment.")
                continue

            # Apply mask to original image
            masked_image = cv2.bitwise_and(image, image, mask=mask)

            # Get bounding coordinates
            coords = np.where(mask > 0)
            y_min, y_max = np.min(coords[0]), np.max(coords[0])
            x_min, x_max = np.min(coords[1]), np.max(coords[1])

            # Add 10% padding
            padding = 0.1
            width = x_max - x_min
            height = y_max - y_min
            x_min_pad = max(0, int(x_min - padding * width))
            x_max_pad = min(w, int(x_max + padding * width))
            y_min_pad = max(0, int(y_min - padding * height))
            y_max_pad = min(h, int(y_max + padding * height))

            # Crop image and mask
            cropped = masked_image[y_min_pad:y_max_pad, x_min_pad:x_max_pad]
            cropped_mask = mask[y_min_pad:y_max_pad, x_min_pad:x_max_pad]

            # Create RGBA image
            rgba = cv2.cvtColor(cropped, cv2.COLOR_RGB2RGBA)
            rgba[:, :, 3] = cropped_mask  # Set alpha channel

            # Calculate proportional scaling
            scale_factor = 0.8 * target_size / max(rgba.shape[0], rgba.shape[1])
            new_width = int(rgba.shape[1] * scale_factor)
            new_height = int(rgba.shape[0] * scale_factor)
            resized = cv2.resize(
                rgba, (new_width, new_height), interpolation=cv2.INTER_AREA
            )

            # Create background canvas
            result_img = np.zeros((target_size, target_size, 4), dtype=np.uint8)
            result_img[:, :, :3] = bg_color
            result_img[:, :, 3] = 255  # Opaque background

            # Calculate centering position
            x_offset = (target_size - new_width) // 2
            y_offset = (target_size - new_height) // 2

            # Alpha compositing
            alpha_s = resized[:, :, 3] / 255.0
            alpha_l = 1.0 - alpha_s

            for c in range(3):
                result_img[
                    y_offset : y_offset + new_height, x_offset : x_offset + new_width, c
                ] = (
                    alpha_s * resized[:, :, c]
                    + alpha_l
                    * result_img[
                        y_offset : y_offset + new_height,
                        x_offset : x_offset + new_width,
                        c,
                    ]
                )

            # Convert to RGB
            segment_img = cv2.cvtColor(result_img, cv2.COLOR_RGBA2RGB)
            segment_images.append(segment_img)

        return segment_images, cloth_names


def split_outfits_to_clothes(
    embedder: FashionClipEncoder,
    segmentation_model: FashionSegmentationModel,
    outfit_dir: str,
    output_dir: str,
):
    completed_idxs = range(0, 11485)
    for outfit_number, outfit_name in enumerate(os.listdir(outfit_dir), 1):

        outfit_path = f"{outfit_dir}/{outfit_name}"
        outfit_idx = outfit_name[6:-4]
        if outfit_idx in completed_idxs:
            continue
        try:
            result = segmentation_model.get_segment_images(outfit_path)

            # Handle case where get_segment_images returns empty list due to invalid segments
            if not result or len(result) == 0:
                continue

            segmented_clothes, cloth_names = result

            if len(segmented_clothes) == 0:
                continue

            # Convert numpy arrays to PIL Images for FashionCLIP
            pil_images = []
            for cloth_img in segmented_clothes:
                # Convert BGR (OpenCV) to RGB (PIL)
                rgb_img = cv2.cvtColor(cloth_img, cv2.COLOR_BGR2RGB)
                pil_img = PILImage.fromarray(rgb_img)
                pil_images.append(pil_img)

            clothes_embeddings = embedder.encode_images(pil_images, normalize=True)

            # calculate similarity matrix (embeddings are already normalized)
            similarity_matrix = np.dot(clothes_embeddings, clothes_embeddings.T)

            # check on similar clothes in one outfit, remove by threshold
            cleaned_clothes = [(segmented_clothes[0], cloth_names[0])]
            for cloth_idx in range(1, len(segmented_clothes)):
                max_similarity = np.max(similarity_matrix[cloth_idx, :cloth_idx])
                if max_similarity < 0.95:
                    cleaned_clothes.append(
                        (segmented_clothes[cloth_idx], cloth_names[cloth_idx])
                    )

            # save clothes in files
            for cloth_img, cloth_class in cleaned_clothes:
                cloth_name = f"cloth{outfit_idx}_{cloth_class}.jpg"
                cloth_path = f"{output_dir}/{cloth_name}"
                cv2.imwrite(cloth_path, cloth_img)

        except ValueError as error:
            print(f"Outfit {outfit_name} is skipped due to ValueError: {error}")
        except Exception as error:
            print(f"Outfit {outfit_name} is skipped due to unexpected error: {error}")

        if outfit_number % 50 == 0:
            print(f"{outfit_number} outfits are already processes!")
    print("All the outfits are processed!")
