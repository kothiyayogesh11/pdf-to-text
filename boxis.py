import pytesseract
from PIL import Image
import pandas as pd
import cv2
import numpy as np
from io import BytesIO
from pdf2image import convert_from_path
from google.cloud import vision
service_account_file="ocr-image-423812-6e9e38c17ca8.json"
client = vision.ImageAnnotatorClient.from_service_account_json(
    service_account_file
)
# Path to the PDF file
pdf_path = '3-5.pdf'

# Convert PDF to images
images = convert_from_path(pdf_path, 350)

# Initialize an empty list to store the parsed data
all_data = []

# Function to parse the OCR text
def parse_text(text):
    lines = text.replace("| Photo","").replace("Photo","").replace("Available","").replace("Age +","Age:").replace("Age !","Age:").replace("Age ","Age:").replace("[","1").replace("House Number =","House Number:").replace("House Number +","House Number :").replace("Name +","Name :").replace("Narne :","Name :").replace("Name =","Name :").replace("Name *","Name :").replace("Name |","Name :").replace("Name ‘","Name :").replace("fqn 2? Gender 2 Mate","Age :69 Gender : Male").replace("Husband's Name?","Husband's Name:").replace("Name !","Name :").replace("Age =","Age :").replace("Gender -","Gender :").replace("::",":")
    lines = lines.strip().split('\n')
    if "Husband's Name ee" in text:
        return []
    print(lines)
    no, id, name, father_name, house_number, age, gender = '', '', '', '', '', '', ''
    for line in lines:
        # print(line, "lines");
        if "Father's Name" in line or "Husband's Name" in line or "Others:" in line:
            father_name = line.split(":")[1].strip()
            continue
        elif "Name" in line and ":" in line:
            name = line.split(":")[1].strip()        
        elif "House Number" in line and ":" in line:
            house_number = line.split(":")[1].strip()
        elif "Age" in line or "Gender" in line:
            parts = line.split(":")[1].strip().split(" ")
            age = parts[0]
            genderArr = line.split(":")
            gender = genderArr[-1] if len(genderArr) > 0 and "Gender" in line else ""
        elif "YFA" in line:
            print(line.split(" "))
            for idval in line.split(" "):
                if "YFA" in idval:
                    id = idval
        
    return [no, id, name, father_name, house_number, age, gender]

def parse_google_text(text):
    text = text.replace("| Photo","").replace("Photo","").replace("Available","").replace("Age +","Age:").replace("Age !","Age:").replace("Age ","Age:").replace("[","1").replace("House Number =","House Number:").replace("House Number +","House Number :").replace("Name +","Name :").replace("Narne :","Name :").replace("Name =","Name :").replace("Name *","Name :").replace("Name |","Name :").replace("Name ‘","Name :").replace("fqn 2? Gender 2 Mate","Age :69 Gender : Male").replace("Husband's Name?","Husband's Name:").replace("Name !","Name :").replace("Age =","Age :").replace("Gender -","Gender :").replace("::",":")
    no, id, name, father_name, house_number, age, gender = '', '', '', '', '', '', ''
    for line in text.splitlines():
        
        if "Father's Name" in line or "Husband's Name" in line or "Others:" in line:
            father_name = line.split(":")[1].strip()
            continue
        elif "Name" in line and ":" in line:
            name = line.split(":")[1].strip()        
        elif "House Number" in line and ":" in line:
            house_number = line.split(":")[1].strip()
        elif "Age" in line or "Gender" in line:
            parts = line.split(":")[1].strip().split(" ")
            age = parts[0]
            genderArr = line.split(":")
            gender = genderArr[-1] if len(genderArr) > 0 and "Gender" in line else ""
        elif "YFA" in line:
            for idval in line.split(" "):
                if "YFA" in idval:
                    id = idval
        elif line.isnumeric():
            no = line
    return [no, id, name, father_name, house_number, age, gender]

def google_detect_text(content):
    """Detects text in the file."""
    # client = vision.ImageAnnotatorClient()

    # with open(path, "rb") as image_file:
        # content = image_file.read()

    image = vision.Image(content=content)

    response = client.text_detection(image=image)
    texts = response.text_annotations
    full_text = response.full_text_annotation.text
    print("Texts:", full_text)
    return full_text
    # this code will manuall extraction
    for text in texts:
        #print(text.description)
        # print(text, "text --")
        vertices = [
            f"({vertex.x},{vertex.y})" for vertex in text.bounding_poly.vertices
        ]

        # print("bounds: {}".format(",".join(vertices)))

    if response.error.message:
        raise Exception(
            "{}\nFor more info on error messages, check: "
            "https://cloud.google.com/apis/design/errors".format(response.error.message)
        )

# Process each image (each page of the PDF)
pagesNo = 0;

for image in images:
    
    # if pagesNo >= 2 and pagesNo <= 37:
    # Convert the image to grayscale
    gray = cv2.cvtColor(np.array(image), cv2.COLOR_BGR2GRAY)
    
    # Apply thresholding to get a binary image
    _, binary_image = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY_INV)
    
    # Find contours
    contours, _ = cv2.findContours(binary_image, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # Sort contours from top to bottom, left to right
    
    contours = sorted(contours, key=lambda c: (cv2.boundingRect(c)[1], cv2.boundingRect(c)[0]))
    
    # Process each contour (each box)
    print(pagesNo+1, "pagesNo")
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        # print(x, y, w, h)
        if w > 100 and h > 100:  # Filter small contours
            # Extract the region of interest (ROI) corresponding to the box
            roi = image.crop((x, y, x + w, y + h))
            # print(roi.show())
            buffered = BytesIO()
            roi.save(buffered, format="JPEG")
            gt = google_detect_text(buffered.getvalue())
            parsed_data = parse_google_text(gt)
            print(parsed_data, "gt")
            
            # Perform OCR on the ROI
            ''' custom_config = r'--oem 3 --psm 6'
            text = pytesseract.image_to_string(roi, config=custom_config, lang="eng") '''
            # print(text)
            # print(text.replace("[","").split("Available\n"))
            # Parse the text
            # parsed_data = parse_text(text)
            # print(parsed_data, "--------Parsed")
            # Append the parsed data to the list
            if len(parsed_data) > 0:
                all_data.append(parsed_data)
            
    pagesNo = pagesNo + 1

# Create a DataFrame
df = pd.DataFrame(all_data, columns=["No","ID",'Name', "Father's Name / Gaurdian Name", 'Address', 'Age', 'Gender'])

# Save DataFrame to CSV
csv_path = 'output.csv'
df.to_csv(csv_path, index=False)

print(f'Data saved to {csv_path}')
