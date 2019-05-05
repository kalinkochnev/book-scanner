# import the necessary packages
from PIL import Image
from txt2pdf import PyText2Pdf
import numpy
import pytesseract
import cv2
import os
import re
from numba import vectorize
import imutils

#TODO: Add destination and file input directory for each class that may require it
#TODO: Make it so functions dont have functions to run inside 
#TODO: Make a thing so the main directory can change and everything still works
#TODO: Find filters to minimize shadows http://bit.ly/2Gf7LPA, understand what the code is doing
#TODO: Make the output of the pdf be in a different directory than the working one, same with the input
#TODO: Look how to make image from text http://bit.ly/2GdRcTY to test ocr
#TODO: Make the OCR use the gpu using cuda

class Book():
    def __init__(self, outputFileName, amountRotate):
        self.outputFileName = outputFileName
        os.chdir("..")
        self.directory = os.getcwd()

        self.bookPages = []

        self.txtPath = ""
        self.pdfPath = ""

        self.amountRotate = amountRotate
        
    def terminalInterface(self):
        print("Welcome to BOCR...")
        print("1. Setup")
        print("2. Rotate images")
        print("3. Convert to txt")
        print("4. Convert to pdf")
        print("5. Create necessary folders and files")
    
    def setup(self):
        #creates test directory to store test files
        testDirectory = os.path.join(self.directory, "testfiles")
        if os.path.isdir(testDirectory) == False:
            os.mkdir(testDirectory)
            #create test txt file
            testTxt = open("testTxt.txt", "w")
            testTxt.write("testing 123")
            testTxt.close()
            #create test img file
            
        #Check if necessary directories are present
        print("Checking if proper files and directories are present...")
        self.checkDirsFiles()
        
        #test the image filtering function
        print("Testing filtering of image")
        testimg = cv2.imread()
        
        #test the ocr 
        print("Testing reading of image")
        
        #test the pdf to txt conversion
        print("Testing conversion of txt to pdf")
        txtName = "testtxt.txt"
        pdfName = "testpdf.pdf"
        newPDF = PyText2Pdf(txtName, pdfName)
        newPDF.convert()
        
    #check if dirs and files exist
    def checkDirsFiles(self):

        imageInputDirExists = False
        imageRotDirExists = False
        outputDirExists = False
        pdfNameExists = False
        txtNameExists = False

        #make input folder if there is none
        imageInputDir = os.path.join(self.directory, "imageinput")
        if os.path.isdir(imageInputDir) == False:
            os.mkdir(imageInputDir)
            print("Input directory not found...")
            print("Creating...")
            imageInputDirExists = False

        #make image rotation folder if there is none
        imageRotDir = os.path.join(self.directory, "rotateimg")
        if os.path.isdir(imageRotDir) == False:
            os.mkdir(imageRotDir)
            print("Image rotation directory not found...")
            print("Creating...")
            imageRotDirExists = False

        #make txt and pdf output folder if there is none
        finalResult = os.path.join(self.directory, "FinalResult")
        if os.path.isdir(finalResult) == False:
            os.mkdir(finalResult)
            print("Result directory not found...")
            print("Creating...")
            outputDirExists = False
        
        processedImage = os.path.join(self.directory, "processedImage")
        if os.path.isdir(processedImage) == False:
            os.mkdir(processedImage)
            print("Processed image directory not found...")
            print("Creating...")

        #Check if a pdf with the chosen name already exists
        if os.path.exists("%s.pdf" % self.outputFileName) == True:
            print("A pdf of that name already exists")
            self.pdfExists = True
            
        #Check if a text file with the chosen name already exists
        if os.path.exists("%s.txt" % self.outputFileName) == True:
            print("A text file with that name already exists")
            self.txtExists = True

        return imageInputDirExists, imageRotDirExists, outputDirExists, pdfNameExists, txtNameExists

    #finds images in folder and puts it into buffer
    def addImages(self):
        imageInputDir = os.path.join(self.directory,"imageinput")
        rotateImageDir = os.path.join(self.directory, "rotateimg")

        #iterate through the files in the rotate folder to then move into the main processing folder
        if os.path.isdir(rotateImageDir):
            for file in os.listdir(rotateImageDir):
                if file.endswith(".jpg") or file.endswith(".png"):
                    #reads the image in black and white, must be or else img.shape fails
                    img = cv2.imread(os.path.join(rotateImageDir, file), 1)
                    """rows, cols = img.shape

                    #rotates the image 180 degrees
                    M = cv2.getRotationMatrix2D((cols/2,rows/2), self.amountRotate, 1)
                    dst = cv2.warpAffine(img,M,(cols,rows))"""

                    dst = imutils.rotate_bound(img, self.amountRotate)  

                    #makes a rotated image and puts it into the main folder and deletes the original
                    cv2.imwrite((imageInputDir + "/" + file +'.png'), dst)
                    #os.remove(os.path.join(rotateImageDir, file))


        #iterates through files in the main folder to then iterate and process
        if os.path.isdir(imageInputDir):
            for file in os.listdir(imageInputDir):
                if file.endswith(".jpg") or file.endswith(".png"):
                    print(os.getcwd())
                    print(("Image with name %s was found" % file))
                    self.bookPages.append(self.get_pagetext(file))
                else:
                    print("Images had incorrect extensions or did not exist")
        else:
            print("The directory did not exist... please restart the program to fix")
            
    #applies filters to the image
    def processImage(self, img_path):
        #output dir
        output_dir = os.path.join(self.directory, "processedImage")
        #extract the file name without the file extension
        file_name = os.path.basename(img_path).split('.')[0]
        file_name = file_name.split()[0]

        #read the image using opencv
        img = cv2.imread(img_path)

        #remove shadows from image
        rgb_planes = cv2.split(img)
        result_planes = []
        result_norm_planes = []
        for plane in rgb_planes:
            dilated_img = cv2.dilate(plane, numpy.ones((7,7), numpy.uint8))
            bg_img = cv2.medianBlur(dilated_img, 21)
            diff_img = 255 - cv2.absdiff(plane, bg_img)
            norm_img = 0
            cv2.normalize(diff_img, norm_img, alpha=0, beta=255, norm_type=cv2.NORM_MINMAX, dtype=cv2.CV_8UC1)
            result_planes.append(diff_img)
            result_norm_planes.append(norm_img)
            print(norm_img)
            
        result_norm = cv2.merge(result_norm_planes)        
        
        #rescale the image, if needed
        img = cv2.resize(img, None, fx=1.5, fy=1.5, interpolation=cv2.INTER_CUBIC)

        #convert to gray
        img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        #apply dilation and erosion to remove some noise
        kernel = numpy.ones((1, 1), numpy.uint8)
        img = cv2.dilate(img, kernel, iterations=1)
        img = cv2.erode(img, kernel, iterations=1)

        #apply blur to smooth out the edges
        img = cv2.GaussianBlur(img, (5, 5), 0)

        #apply threshold to get image with only b and white (binarization)
        img = cv2.threshold(img, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]

        #save the filtered image in the output directory
        save_path = os.path.join(output_dir, file_name + "_filter_" + "foomethod" + ".jpg") # str(method)
        cv2.imwrite(save_path, img)

        return img
    
    #gets string/text from image
    def get_pagetext(self, file):
        #directory of the images
        imageInputDir = os.path.join(self.directory,"imageinput")
        
        #recognize text with teseract for python
        result = pytesseract.image_to_string(self.processImage(os.path.join(imageInputDir, file)), lang="eng")
        
        #Puts pages into list
        self.bookPages.append(result)
        
    #prints out all the pages
    def showAllPages(self):
        for idx,page in enumerate(self.bookPages):
            print("--------------  Page %s  --------------\n" % (idx+1))
            print(page)

    #prints out a specific page
    def showSpecificPage(self, pagenumber):
        print("--------------  Page %s  --------------\n" % (pagenumber))
        print(self.bookPages[pagenumber])
    
    #removes non-ascii characters to prevent pdf problems
    def remove_non_ascii(self, text):
        removeNon = re.sub(r'[^\x00-\x7F]+',' ', text)
        removeDash = removeNon.replace("-", "")
        return removeDash

    #takes the read character and puts them into a text file
    def txtFile(self):
        txtName = "%s%s" % (self.outputFileName, ".txt")

        #creates a text file from the buffer
        txtFile = open(txtName, "w")
        for idx, page in enumerate(self.bookPages):
            onlyAscii = self.remove_non_ascii(str(page))
            txtFile.write(str(page))
    
    #converts the text file to the pdf
    def pdfFile(self):
        pdfName = "%s%s" % (self.outputFileName, ".pdf")
        txtName = "%s%s" % (self.outputFileName, ".txt")

        #converts the text file to a pdf
        self.txtFile()
        newPDF = PyText2Pdf(txtName, pdfName)
        newPDF.convert()

        #Moves the pdf to the output path
        finalResult = os.path.join(self.directory, "FinalResult")
        os.rename(pdfName, os.path.join(finalResult, pdfName))

if __name__ == "__main__":
    myBook = Book("WorkPls", 270)
    myBook.addImages()
    bool = myBook.checkDirsFiles()
    #0 is imageInput, 1 is rotDir, 2 is outputDir, 3 is pdfExists, 4 is txtExists
    if bool[3] == False or bool[4] == False:
        myBook.pdfFile()
        print("Your pdf is ready")
    else:
        print("Files were not created")