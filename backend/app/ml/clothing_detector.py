from ultralytics import YOLO
import cv2
import numpy as np

# trained model
model = YOLO('app/ml/best.pt')

def get_clothes_from_img(img_path):
    # read the image
    img = cv2.imread(img_path)
    # get the height and width for future calculations
    
    img_height, img_width, _ = img.shape
    names = {
        0: 'sunglass',
        1: 'hat',
        2: 'jacket',
        3: 'shirt',
        4: 'pants',
        5: 'shorts',
        6: 'skirt',
        7: 'dress',
        8: 'bag',
        9: 'shoe'
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
            name = str(names[name]) + f'_{count_clothes[name] - 1}'
        else:
            count_clothes[name] = 1
            name = names[name] + '_0'
        x = float(x)
        y = float(y)
        width = float(width)
        height = float(height)
        x1_real = int(np.abs(x - (width/2)) * img_width)
        x2_real = int(np.abs(x + (width/2)) * img_width)
        y1_real = int(np.abs(y + (height/2)) * img_height)
        y2_real = int(np.abs(y - (height/2)) * img_height)
        parts.append((name,img[y2_real:y1_real, x1_real:x2_real]))
    return parts