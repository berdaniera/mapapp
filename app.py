import os
from flask import Flask, render_template, request, jsonify, Markup
import stripe
import datetime
import codecs
import math
import tempfile
import uuid
import shutil
from itertools import product
import zipfile
from subprocess import call
import rasterio
from scipy import ndimage
import matplotlib
matplotlib.use('Agg')
from matplotlib import pyplot as plt
import matplotlib.font_manager as fm

stripe_keys = {
  'secret_key': os.environ['SECRET_KEY'],
  'publishable_key': os.environ['PUBLISHABLE_KEY']
}
stripe.api_key = stripe_keys['secret_key']

app = Flask(__name__)

di = "/home/aaron/srtm/"
ff = [f for f in os.listdir(di)]
fonts = fm.findSystemFonts()
path = [x for x in fonts if 'Lato-Light.ttf' in x][0]
prop = fm.FontProperties(fname=path)
linecol = "#333333"
narr = range(0,9000,50)
wide = range(0,9000,200)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/_proof', methods=['POST'])
def proof():
    rfn = "elly"+str(uuid.uuid4())[:6] # random file name for object
    # Collect variables
    v = {}
    v['xmin'] = request.json['xmin']
    v['xmax'] = request.json['xmax']
    v['ymin'] = request.json['ymin']
    v['ymax'] = request.json['ymax']
    v['textm'] = request.json['textm']
    v['textc'] = request.json['textc']
    v['size'] = request.json['size']
    v['shape'] = request.json['shape']
    v['clip'] = request.json['clip']
    #
    zooml = request.json['zoom']
    #
    lats = range(int(math.floor(v['ymin'])), int(math.ceil(v['ymax'])))
    lngs = range(int(math.floor(v['xmin'])), int(math.ceil(v['xmax'])))
    if(lats[1]==lats[0]):
        lats[1] = lats[1]+1
    if(lngs[1]==lngs[0]):
        lngs[1] = lngs[1]+1
    #
    zdir = tempfile.mkdtemp()
    lat = ["S"+str(-l).zfill(2) if (l<0) else "N"+str(l).zfill(2) for l in lats]
    lng = ["W"+str(-l).zfill(3) if (l<0) else "E"+str(l).zfill(3) for l in lngs]
    gg = list(product(lat, lng))
    rasts = [g[0]+g[1]+".SRTMGL3.hgt.zip" for g in gg]
    rastl = [di+r for r in rasts if r in ff]
    #
    # list of rasters that were unzipped
    def uzr(r):
        z2 = zipfile.ZipFile(r, 'r')
        z2.extractall(zdir)
        nm = z2.namelist()[0]
        z2.close()
        return(nm)
    #
    lx = [uzr(r) for r in rastl]
    mos = open(zdir+"/mosaic.txt", "w")
    mos.write('\n'.join(lx))
    mos.close()
    # BUILD RASTER
    reso = 0.000833333
    if zooml==3:
        reso = reso*8
    elif zooml==4:
        reso = reso*6
    elif zooml==5:
        reso = reso*4
    else:
        reso = reso*2
    comm = "cd "+zdir+" && "+\
        "gdalbuildvrt -overwrite -input_file_list mosaic.txt out.vrt && "+\
        "gdalwarp --config GDAL_CACHEMAX 500 -wm 500 -q -overwrite -dstnodata 0 "+\
        "-te "+str(v['xmin'])+" "+str(v['ymin'])+" "+str(v['xmax'])+" "+str(v['ymax'])+" -tr "+str(reso)+" "+str(reso)+" -r average out.vrt out.tif"
    call(comm, shell=True)
    with rasterio.open(zdir+'/out.tif', 'r+') as r:
        rr = r.read()  # read all raster values
        rr = ndimage.filters.uniform_filter(rr, size=21) # 4km moving average
        r.write(rr)
    #
    # IF CLIPPING
    if (v['clip'] != ""): # reproject to equal area
        if (v['clip'][:1]=="s"):
            # Make shapefile
            inshp = '/home/aaron/shapes/cb_2015_us_state_500k/cb_2015_us_state_500k.shp'
            inreg = "\"STUSPS='"+v['clip'][1:]+"'\" "
        else:
            inshp = '/home/aaron/shapes/TM_WORLD_BORDERS-0.3/TM_WORLD_BORDERS-0.3.shp'
            inreg = "\"ISO2='"+v['clip'][1:]+"'\" "
        comm = "ogr2ogr -f \"ESRI Shapefile\" "+zdir+"/crop.shp -where "+inreg+inshp
        call(comm, shell=True)
        ex = [min(lats),max(lats),min(lngs),max(lngs)]
        #proje = "+proj=lcc +lat_1="+str(ex[0])+" +lat_2="+str(ex[1])+" +lat_0="+str((ex[0]+ex[1])/2)+" +lon_0="+str((ex[2]+ex[3])/2)+" +x_0=0 +y_0=0 +ellps=GRS80 +datum=NAD83 +units=m"
        proje = "+proj=merc +lon_0=0 +k=1 +x_0=0 +y_0=0 +a=6378137 +b=6378137 +towgs84=0,0,0,0,0,0,0 +units=m +no_defs"
        # clipcomm = "gdalwarp --config GDAL_CACHEMAX 500 -wm 500 -s_srs '+proj=longlat +datum=WGS84 +no_defs +ellps=WGS84 +towgs84=0,0,0' -t_srs '"+proje+\
        #     "' -overwrite -dstnodata 0 -r average -cutline "+zdir+"/crop.shp "+zdir+"/out.tif "+zdir+"/outc.tif"
        clipcomm = "gdalwarp --config GDAL_CACHEMAX 500 -wm 500 -s_srs '+proj=longlat +datum=WGS84 +no_defs +ellps=WGS84 +towgs84=0,0,0' -t_srs '"+proje+\
            "' -overwrite -dstnodata 0 -r average -te "+str(v['xmin'])+" "+str(v['ymin'])+" "+str(v['xmax'])+" "+str(v['ymax'])+\
            " -te_srs '+proj=longlat +ellps=WGS84 +datum=WGS84 +no_defs' -cutline "+zdir+"/crop.shp "+zdir+"/out.tif "+zdir+"/outc.tif"
        call(clipcomm, shell=True)
        rrr = rasterio.open(zdir+'/outc.tif','r').read()
    else: # reproject to web mercator...
        proje = "+proj=merc +lon_0=0 +k=1 +x_0=0 +y_0=0 +a=6378137 +b=6378137 +towgs84=0,0,0,0,0,0,0 +units=m +no_defs"
        clipcomm = "gdalwarp --config GDAL_CACHEMAX 500 -wm 500 -s_srs '+proj=longlat +datum=WGS84 +no_defs +ellps=WGS84 +towgs84=0,0,0' -t_srs '"+proje+\
            "' -overwrite -dstnodata 0 -r average "+zdir+"/out.tif "+zdir+"/outc.tif"
        call(clipcomm, shell=True)
        rrr = rasterio.open(zdir+'/outc.tif','r').read()
    #
    # PLOTS
    #rrr[rrr<0] = 0
    maxele = rrr.max()
    minele = rrr.min()
    ells = [n for n in narr if n < maxele]
    if (maxele-minele)>2500:
        ells = [e for e in ells if e%100==0]
    #
    cols = ["#333333" if z%200==0 else "#777777" for z in ells]
    #
    if(v['shape']=="portrait"):
        wid = int(v['size'][:2])
        hei = int(v['size'][2:])
    else:
        hei = int(v['size'][:2])
        wid = int(v['size'][2:])
    #
    # 72 points is one inch
    xoff = [1./wid, (wid-1.)/wid]
    yoff = [3./hei, (hei-1.)/hei]
    #
    # PLOT
    fig = plt.figure(figsize=(wid,hei))
    ax = fig.add_subplot(111, aspect='equal')
    ax.contour(rrr[0], origin='image', levels=ells, colors=cols, linewidths=0.75, corner_mask=True, antialiased=True, extend='neither')
    ax.axis('off')
    ax.text(0.5, 1.5/hei, v['textm'], transform=fig.transFigure, ha='center',va='bottom', fontsize=60, fontproperties=prop)
    ax.text(0.5, 1./hei, v['textc'], transform=fig.transFigure, ha='center',va='bottom', fontsize=30, fontproperties=prop)
    fig.subplots_adjust(left=xoff[0], bottom=yoff[0], right=xoff[1], top=yoff[1], wspace=0, hspace=0)
    fig.savefig("/home/aaron/maps/"+rfn+".pdf")
    #
    s=6
    # save thumbnail too...
    figt = plt.figure(figsize=(wid/s,hei/s),dpi=100)
    axt = figt.add_subplot(111, aspect='equal')
    axt.contour(rrr[0], origin='image', levels=ells, colors=cols, linewidths=0.5, corner_mask=True, antialiased=True, extend='neither')
    axt.axis('off')
    axt.text(0.5, 1.5/hei, v['textm'], transform=figt.transFigure, ha='center',va='bottom', fontsize=60/s, fontproperties=prop)
    axt.text(0.5, 1./hei, v['textc'], transform=figt.transFigure, ha='center',va='bottom', fontsize=30/s, fontproperties=prop)
    axt.text(0.5, 0.5, 'PROOF', transform=figt.transFigure, ha='center', va='center', fontsize=72, weight='bold', alpha=0.4)
    figt.subplots_adjust(left=xoff[0], bottom=yoff[0], right=xoff[1], top=yoff[1], wspace=0, hspace=0)
    figt.savefig("/home/aaron/elly/static/proofs/"+rfn+".png")
    shutil.rmtree(zdir)
    return jsonify(result=rfn, params=v)

@app.route('/_coupon-check', methods=['POST'])
def coupon():
    coupons = {"SAVE10":0.1, "SNOWSNOW":0.15}
    code = request.json['coupon']
    if code in coupons:
        res = 1
        disc = coupons[code]
    else:
        res = 0
        disc = 0
    return jsonify(res=res, disc=disc)

@app.route('/_email-list', methods=['POST'])
def email():
    email = request.json['email']
    edb = open("/home/aaron/elly/email-list.csv","a")
    edb.write(email+"\n")
    edb.close()
    return jsonify(result="success")

@app.route('/charge', methods=['POST'])
def charge():
    # If CHARGED, move the files
    amount = int(request.form['orderAmt'])
    token = request.form['stripeToken']
    orderid = request.form['orderId']
    orderdat = request.form['orderData']
    # Create a charge: this will charge the user's card
    try:
      charge = stripe.Charge.create(
          amount=amount, # Amount in cents
          currency="usd",
          source=token,
          description="ellymap.com order",
          metadata={"order_id": orderid}
      )
      response = Markup("<h2>Thanks for your order!</h2><p>We'll send you an email when it ships!</p>")
      db = codecs.open("/home/aaron/elly/orders.csv","a",'utf-8')
      # Add data to order database...
      # date, stripeToken, orderId, orderData, amount, name, email, address, city, state, zip, country
      orderdat = (datetime.date.today().strftime("%Y-%m-%d") +","+ token +","+ orderid +",'"+orderdat+"',"+\
        str(amount/100) +","+ request.form['name'] +","+  request.form['email'] +","+  request.form['address'] +","+\
        request.form['city'] +","+ request.form['state'] +","+ request.form['zip'] +","+ request.form['country'] +"\n")
      db.write(orderdat)
      db.close()
    except stripe.error.CardError as e:
      # The card has been declined
      amount = 0
      response = Markup("<h2>Something went wrong...</h2><p>Please try again.</p>")
    #
    chargedamt = amount/100
    #
    return render_template('charge.html', amount=chargedamt, order=orderid, response=response)

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=9898)
