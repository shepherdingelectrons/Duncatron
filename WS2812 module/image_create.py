# Generates a Python file ("RAMimages.py") with bytearrays from a list of images.
# The loop opens an image in the list, then resamples it for a 16x16 image, and exacts
# the RGB data in the necessary way for injecting into the RAM on the 8-bit computer later.

from PIL import Image

def RAMaddress(x,y):
    if x&1==0: # even columns
        addr = (x*16)+y
    else:   # odd columns
        addr = (x*16)+(15-y)
    return 3*addr

def resample(px,py):
    # px must be between 0 and wn-1
    # py must be between 0 and hn-1
    wn = 16
    hn = 16
    w = im.width
    h = im.height

    w_div = w/wn
    h_div = h/wn

    spx = int(w_div * (px+0.5))
    spy = int(h_div * (py+0.5))

    return im.getpixel((spx,spy))
    
#Read image
folder = ""
imagelist = ["rainbow_square.png","hackaday.bmp"]

f = open(folder+"RAMimages.py","w") # Generates a Python file with bytearrays that can be imported

for image in imagelist:
    im = Image.open( folder+image)
    im = im.convert('RGB')

    RAMsize = 256*3
    RAM = bytearray(RAMsize)

    for x in range(0,16):
        for y in range(0,16):
            r,g,b = resample(x,y)
            RAMaddr = RAMaddress(x,y)

            RAM[RAMaddr]=g
            RAM[RAMaddr+1]=r
            RAM[RAMaddr+2]=b
    name=image.split('.')[0]
    
    f.write(name+"="+str(RAM)+"\n")
f.close()


