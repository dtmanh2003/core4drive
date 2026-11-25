import cv2
from pathlib import Path
out = Path(__file__).resolve().parent / "aruco_4x4_id7.png"
try:
    aruco = cv2.aruco
    dictionary = aruco.getPredefinedDictionary(aruco.DICT_4X4_50)
    img = aruco.generateImageMarker(dictionary, 7, 600)
    cv2.imwrite(str(out), img)
    print("saved", out)
except Exception as e:
    print("OpenCV aruco not available:", e)
    print("Install opencv-contrib-python if needed.")
