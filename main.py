import base64
import datetime
import os.path
import time
import razorpay
import json
from flask import Flask, request, redirect, url_for, render_template, session
import firebase_admin
import random
from firebase_admin import credentials, firestore
from MailSent import send_email
from datetime import datetime
cred = credentials.Certificate("key.json")
firebase_admin.initialize_app(cred)
app = Flask(__name__)
app.secret_key = "OnlineSkinCare@123"
UPLOAD_FOLDER = 'static/uploads/'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'gif'])
#key_id,key_secret
#rzp_test_bwFUQvFdcBdnqI, NN9Yi7mL7s15FtqgWGOLr5Zp
RAZOR_KEY_ID="rzp_test_bwFUQvFdcBdnqI"
RAZOR_KEY_SECRET="NN9Yi7mL7s15FtqgWGOLr5Zp"
razorpay_client = razorpay.Client(auth=(RAZOR_KEY_ID, RAZOR_KEY_SECRET))

ptypes=["Exfoliators","Toners","Cleansers","Serums","Moisturizers",
        "Eye Creams","Sunscreens","Face Masks","Lip Care Products",
        "Spot Treatments"]

@app.route('/customermakeappointment', methods=['POST','GET'])
def customermakeappointment():
    try:
        cartid=request.args['id']
        session['cartid']=cartid
        db = firestore.client()
        newdata_ref = db.collection('newdoctor')
        newdata = newdata_ref.get()
        data=[]
        for doc in newdata:
            data.append(doc.to_dict())
        print("Users Data " , data)
        return render_template("customermakeappointment.html", data=data)
    except Exception as e:
        return str(e)

@app.route('/customermakeappointment1', methods=['POST','GET'])
def customermakeappointment1():
    try:
        id = request.args['id']
        db = firestore.client()
        dbref = db.collection('newdoctor')
        data = dbref.document(id).get().to_dict()
        print("Doctor Data ", data)
        time = datetime.now()
        today=time.strftime("%Y-%m-%d")
        return render_template("customermakeappointment1.html", data=data, today=today)
    except Exception as e:
        return str(e)

@app.route('/customermakeappointment2', methods=['POST','GET'])
def customermakeappointment2():
    try:
        print("Add New doctor page")
        msg=""
        if request.method == 'POST':
            cartid=session['cartid']
            userid=session['userid']
            did = request.form['did']
            fname = request.form['fname']
            lname = request.form['lname']
            atime = request.form['atime']
            adate = request.form['adate']
            email = request.form['email']
            phnum = request.form['phnum']
            id = str(round(time.time()))            
            json = {'id': id,'CartId':cartid,'DoctorId':did,
                    'UserId':userid,
                    'FirstName': fname,'LastName':lname,
                    'AppointDate': adate,'AppointTime':atime,
                    'EmailId': email,'PhoneNumber':phnum,
                    'DoctorStatus': 'RequestSent'}
            db = firestore.client()
            newdb_ref = db.collection('newappointment')
            newdb_ref.document(id).set(json)
        return redirect(url_for("customerviewappointments"))
    except Exception as e:
        return str(e)

@app.route('/customerviewappointments', methods=['GET','POST'])
def customerviewappointments():
    try:
        db = firestore.client()
        data_ref = db.collection('newappointment')
        newdata = data_ref.get()
        id = int(session['userid'])
        print('UserId : ', id)
        data = []
        for doc in newdata:
            temp = doc.to_dict()
            if (int(temp['UserId']) == id):
                data.append(doc.to_dict())
        return render_template("customerviewappointments.html", data=data)
    except Exception as e:
        return str(e)

@app.route('/doctorupdatestatus', methods=['POST','GET'])
def doctorupdatestatus():
    print("Doctor Update Status")
    status = request.args['status']
    id = request.args['id']
    db = firestore.client()
    data_ref = db.collection(u'newappointment').document(id)
    data_ref.update({u'DoctorStatus': status})
    return redirect(url_for("doctorviewappointments"))

@app.route('/customeraddtocart1', methods=['GET','POST'])
def customeraddtocart1():
    try:
        print("Add New Product page")
        msg=""
        if request.method == 'POST':
            pid = request.form['pid']
            pname = request.form['pname']
            ptype = request.form['ptype']
            qty = request.form['qty']
            rqty = request.form['reqqty']
            price = request.form['price']
            total = request.form['total']
            userid = session['userid']
            id = str(random.randint(1000, 9999))
            json = {'id': id,'ProductId':pid,
                    'ProductName': pname,'ProductType':ptype,
                    'ReqQuantity': rqty,'Price':price, 'Total':total,
                    'UserId': userid,'FileName':userid,'PaymentStatus':'PaymentNotDone'}
            db = firestore.client()
            newdb_ref = db.collection('newaddtocart')
            newdb_ref.document(id).set(json)

            db = firestore.client()
            data_ref = db.collection(u'newproduct').document(pid)
            data_ref.update({u'Quantity': int(qty)-int(rqty)})
        return redirect("customerviewcart")
    except Exception as e:
        return str(e)

@app.route('/customerviewcart', methods=["POST","GET"])
def customerviewcart():
    try:
        userid=session['userid']
        tablename = "newaddtocart"
        data,total,context,currency,amount=[],0, {},'INR',0
        db = firestore.client()
        newdb_ref = db.collection(tablename)
        dbdata = newdb_ref.get()
        data = []
        for doc in dbdata:
            temp=doc.to_dict()
            if (doc.to_dict()['UserId'] == str(userid)):
                data.append(doc.to_dict())
                if (str(temp['PaymentStatus']) != "PaymentDone"):
                    total = total + int(temp['Total'])
        if (total > 0):
            amount = total * 100
        else:
            amount = 200
        session['total'] = amount
        # Create a Razorpay Order
        razorpay_order = razorpay_client.order.create(dict(amount=amount,
                                                           currency=currency,
                                                           payment_capture='0'))
        print("Data : ", data, " Total : ", total)
        # order id of newly created order.
        razorpay_order_id = razorpay_order['id']
        callback_url = 'usermakepayment'
        # we need to pass these details to frontend.
        context['razorpay_order_id'] = razorpay_order_id
        context['razorpay_merchant_key'] = RAZOR_KEY_ID
        context['razorpay_amount'] = amount
        context['currency'] = currency
        context['callback_url'] = callback_url
        print("Context : ", context)
        session['context']=context
        return render_template("customerviewcart.html", data=data, total=total, context=context)
    except Exception as e:
        return str(e)

@app.route('/usermakepayment', methods=["POST","GET"])
def usermakepayment():
    try:
        print("User Make Payment Page")
        userid = session['userid']
        context = session['context']
        db = firestore.client()
        data_ref = db.collection('newaddtocart')
        newdata = data_ref.get()
        array = []
        for doc in newdata:
            temp = doc.to_dict()
            print("Temp : ", temp)
            if (int(temp['UserId']) == int(userid) and temp['PaymentStatus'] != "PaymentDone"):
                array.append(temp['id'])
        print("User Cart Ids : ", array)
        print("User Cart Ids Length : ",len(array))
        time = datetime.now()
        now = time.strftime("%m/%d/%y %H:%M:%S")
        print("User Cart Ids : ", array)
        for x in array:
            print("x = ", x)
            db = firestore.client()                
            data_ref = db.collection(u'newaddtocart').document(x)
            data_ref.update({u'PaymentStatus': 'PaymentDone'})            # get the required parameters from post request.
            data_ref.update({u'RazorPay_OrderId': context['razorpay_order_id']})
            data_ref.update({u'RazorPay_Merchant_Key': context['razorpay_merchant_key']})
            data_ref.update({u'PaymentDate': now})                
        payment_id = request.form['razorpay_payment_id', '']
        razorpay_order_id = request.form['razorpay_order_id', '']
        signature = request.form['razorpay_signature', '']
        params_dict = {
                'razorpay_order_id': razorpay_order_id,
                'razorpay_payment_id': payment_id,
                'razorpay_signature': signature
        }
        total = session['total']
        razorpay_client.payment.capture(payment_id, total)
        print("Res : ", json.dumps(razorpay_client.payment.fetch(payment_id)))
            # verify the payment signature.
        result = razorpay_client.utility.verify_payment_signature(
                params_dict)
        print("Result : ", result)
        if result is not None:
            amount = total  # Rs. 200
            try:
                    # capture the payemt
                razorpay_client.payment.capture(payment_id, amount)
                    # render success page on successful caputre of payment
                return render_template('paymentsuccess.html')
            except:
                    # if there is an error while capturing payment.
                return render_template('paymentsuccess.html')
        else:
                # if signature verification fails.
            return render_template('paymentsuccess.html')
    except Exception as e:
            # if we don't find the required parameters in POST data
            #return HttpResponseBadRequest()
        print("Exception : ", e)
        return render_template('paymentsuccess.html')

@app.route('/customerviewreports', methods=['POST','GET'])
def customerviewreports():
    try:
        db = firestore.client()
        data_ref = db.collection('newaddtocart')
        newdata = data_ref.get()
        id = int(session['userid'])
        print('UserId : ', id)
        data = []
        for doc in newdata:
            temp = doc.to_dict()
            print("Temp : ", temp)
            if (int(temp['UserId']) == id):
                data.append(doc.to_dict())
        return render_template("customerviewreports.html", data=data)
    except Exception as e:
        return str(e)

@app.route('/')
def index():
    try:
        return render_template("index.html")
    except Exception as e:
        return str(e)

@app.route('/usermainpage')
def usermainpage():
    try:
        return render_template("usermainpage.html")
    except Exception as e:
        return str(e)

@app.route('/doctorforgotpassword')
def doctorforgotpassword():
    try:
        return render_template("doctorforgotpassword.html")
    except Exception as e:
        return str(e)

@app.route('/doctorenterotppage')
def doctorenterotppage():
    try:
        return render_template("doctorenterotppage.html")
    except Exception as e:
        return str(e)

@app.route('/doctorchecking', methods=['POST'])
def doctorchecking():
    try:
        if request.method == 'POST':
            uname = request.form['uname']
            email = request.form['email']
        print("Uname : ", uname, " Email : ", email);
        db = firestore.client()
        dbref = db.collection('newdoctor')
        userdata = dbref.get()
        data = []
        for doc in userdata:
            print(doc.to_dict())
            print(f'{doc.id} => {doc.to_dict()}')
            data.append(doc.to_dict())
        flag = False
        for temp in data:
            if uname == temp['UserName'] and email == temp['EmailId']:
                session['username'] = uname
                session['emailid'] = email
                session['userid'] = temp['id']
                flag = True
                break
        if (flag):
            otp = random.randint(1000, 9999)
            print("OTP : ", otp)
            session['toemail'] = email
            session['uname'] = uname
            session['otp'] = otp
            print("User Id : ", session['userid'])
            return render_template("doctorgenerateotp.html", uname=uname, toemail=email, otp=otp,
                                                        redirecturl= 'http://127.0.0.1:5000/doctorenterotppage')
        else:
            return render_template("doctorforgotpassword.html", msg="UserName/EmailId is Invalid")
    except Exception as e:
        return str(e)

@app.route('/doctorcheckotppage', methods=['POST'])
def doctorcheckotppage():
    if request.method == 'POST':
        storedotp=session['otp']
        enteredotp = request.form['otp']
        print("Entered OTP : ", enteredotp, " Stored OTP : ", storedotp)
        if(int(storedotp)==int(enteredotp)):
            return render_template("doctorpasswordchangepage.html", msg="You can update your password")
        else:
            return render_template("doctorenterotppage.html", msg="Incorrect OTP")
    return render_template("doctorenterotppage.html", msg="Incorrect OTP")

@app.route('/doctorpasswordchangepage', methods=['POST'])
def doctorpasswordchangepage():
    print("Password Change Page")
    if request.method == 'POST':
        uname = request.form['uname']
        pwd = request.form['pwd']

        db = firestore.client()
        newdoctor_ref = db.collection('newdoctor')
        doctordata = newdoctor_ref.get()
        data = []
        for doc in doctordata:
            print(doc.to_dict())
            print(f'{doc.id} => {doc.to_dict()}')
            data.append(doc.to_dict())
        id=""
        for doc in data:
            print("Document : ", doc)
            if(doc['UserName']==uname):
                id=doc['id']
        db = firestore.client()
        data_ref = db.collection(u'newdoctor').document(id)
        data_ref.update({u'Password': pwd})
        print("Password Updated Success")
        return render_template("doctorlogin.html", msg="Password Updated Success")
    return render_template("doctorlogin.html", msg="Password Not Updated")

@app.route('/index')
def indexpage():
    try:
        return render_template("index.html")
    except Exception as e:
        return str(e)

@app.route('/logout')
def logoutpage():
    try:
        session['id']=None
        return render_template("index.html")
    except Exception as e:
        return str(e)

@app.route('/about')
def aboutpage():
    try:
        return render_template("about.html")
    except Exception as e:
        return str(e)

@app.route('/services')
def servicespage():
    try:
        return render_template("services.html")
    except Exception as e:
        return str(e)

@app.route('/gallery')
def gallerypage():
    try:
        return render_template("gallery.html")
    except Exception as e:
        return str(e)

@app.route('/adminlogin', methods=['GET','POST'])
def adminloginpage():
    msg=""
    if request.method == 'POST':
        uname = request.form['uname'].lower()
        pwd = request.form['pwd'].lower()
        print("Uname : ", uname, " Pwd : ", pwd)
        if uname == "admin" and pwd == "admin":
            return render_template("adminmainpage.html")
        else:
            msg = "UserName/Password is Invalid"
    return render_template("adminlogin.html", msg=msg)

@app.route('/customerlogin', methods=['GET','POST'])
def customerlogin():
    msg=""
    if request.method == 'POST':
        uname = request.form['uname']
        pwd = request.form['pwd']

        db = firestore.client()
        dbref = db.collection('newcustomer')
        userdata = dbref.get()
        data = []
        for doc in userdata:
            print(doc.to_dict())
            print(f'{doc.id} => {doc.to_dict()}')
            data.append(doc.to_dict())
        flag = False
        for temp in data:
            print("Pwd : ", temp['Password'])
            #decMessage = fernet.decrypt(temp['Password']).decode()
            decode = base64.b64decode(temp['Password']).decode("utf-8")
            if uname == temp['UserName'] and pwd == decode:
                session['userid'] = temp['id']
                flag = True
                break
        if (flag):
            return render_template("customermainpage.html")
        else:
            msg = "UserName/Password is Invalid"
    return render_template("customerlogin.html", msg=msg)

@app.route('/doctorlogin', methods=['GET','POST'])
def doctorloginpage():
    msg=""
    if request.method == 'POST':
        uname = request.form['uname']
        pwd = request.form['pwd']
        db = firestore.client()
        dbref = db.collection('newdoctor')
        userdata = dbref.get()
        data = []
        for doc in userdata:
            print(doc.to_dict())
            print(f'{doc.id} => {doc.to_dict()}')
            data.append(doc.to_dict())
        flag = False
        for temp in data:
            #decMessage = fernet.decrypt(temp['Password']).decode()
            decode = base64.b64decode(temp['Password']).decode("utf-8")
            if uname == temp['UserName'] and pwd == decode:
                session['userid'] = temp['id']
                flag = True
                break
        if (flag):
            return render_template("doctormainpage.html")
        else:
            msg = "UserName/Password is Invalid"
    return render_template("doctorlogin.html", msg=msg)

@app.route('/doctorviewprofile', methods=['GET','POST'])
def doctorviewprofile():
    try:
        id = session['userid']
        db = firestore.client()
        dbref = db.collection('newdoctor')
        data = dbref.document(id).get().to_dict()
        print("User Data ", data)
        return render_template("doctorviewprofile.html", data=data)
    except Exception as e:
        return str(e)

@app.route('/customeraddtocart', methods=['GET','POST'])
def customeraddtocart():
    try:
        id=request.args['id']
        db = firestore.client()
        dbref = db.collection('newproduct')
        data = dbref.document(id).get().to_dict()
        print("Product Data ", data)
        return render_template("customeraddtocart.html", data=data)
    except Exception as e:
        return str(e)

@app.route('/customerviewprofile', methods=['GET','POST'])
def customerviewprofile():
    try:
        id=session['userid']
        db = firestore.client()
        dbref = db.collection('newcustomer')
        data = dbref.document(id).get().to_dict()
        print("User Data ", data)
        return render_template("customerviewprofile.html", data=data)
    except Exception as e:
        return str(e)

@app.route('/doctorviewfullreport', methods=['GET','POST'])
def doctorviewfullreport():
    try:
        id=request.args['id']
        db = firestore.client()
        dbref = db.collection('newaddtocart')
        data = dbref.document(id).get().to_dict()
        print("Cart Data ", data)
        return render_template("doctorviewfullreport.html", data=data)
    except Exception as e:
        return str(e)

@app.route('/adminviewfullreport', methods=['GET','POST'])
def adminviewfullreport():
    try:
        id=request.args['id']
        db = firestore.client()
        dbref = db.collection('newaddtocart')
        data = dbref.document(id).get().to_dict()
        print("Cart Data ", data)
        return render_template("adminviewfullreport.html", data=data)
    except Exception as e:
        return str(e)

@app.route('/customerviewfullreport', methods=['GET','POST'])
def customerviewfullreport():
    try:
        id=request.args['id']
        db = firestore.client()
        dbref = db.collection('newaddtocart')
        data = dbref.document(id).get().to_dict()
        print("Cart Data ", data)
        return render_template("customerviewfullreport.html", data=data)
    except Exception as e:
        return str(e)

@app.route('/newcustomer', methods=['POST','GET'])
def newcustomer():
    try:
        msg=""
        print("Add New Customer page")
        if request.method == 'POST':
            fname = request.form['fname']
            lname = request.form['lname']
            uname = request.form['uname']
            pwd = request.form['pwd']
            email = request.form['email']
            phnum = request.form['phnum']
            address = request.form['address']
            id = str(random.randint(1000, 9999))
            #encMessage = fernet.encrypt(pwd.encode())
            encode = base64.b64encode(pwd.encode("utf-8"))
            print("str-byte : ", encode)
            json = {'id': id,
                        'FirstName': fname, 'LastName': lname,
                        'UserName': uname, 'Password': encode,
                        'EmailId': email, 'PhoneNumber': phnum,
                        'Address': address}
            db = firestore.client()
            newuser_ref = db.collection('newcustomer')
            newuser_ref.document(id).set(json)
            print("User Customer Success")
            msg = "New Customer Inserted Success"
        return render_template("newcustomer.html", msg=msg)
    except Exception as e:
        return str(e)

@app.route('/useraddcrop', methods=['POST','GET'])
def useraddcrop():
    try:
        msg=""
        print("Add New User page")
        if request.method == 'POST':
            cname = request.form['cname']
            ctype = request.form['ctype']
            qty = request.form['qty']
            price = request.form['price']
            comments = request.form['comments']
            userid=session['userid']
            farmername = session['farmername']
            id = str(random.randint(1000, 9999))
            json = {'id': id, 'UserId':userid,
                    'FarmerName':farmername,
                    'CropName': cname, 'CropType': ctype,
                    'Quantity': qty, 'Price': price,
                    'Comments': comments}
            db = firestore.client()
            newuser_ref = db.collection('newcrop')
            newuser_ref.document(id).set(json)
            print("Crop Inserted Success")
            msg = "New Crop Added Success"
        return render_template("useraddcrop.html", msg=msg)
    except Exception as e:
        return str(e)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/adminaddproduct', methods=['POST','GET'])
def adminaddproduct():
    try:
        print("Add New Product page")
        msg=""
        if request.method == 'POST':
            pname = request.form['pname']
            ptype = request.form['ptype']
            qty = request.form['qty']
            price = request.form['price']
            file = request.files['file']
            description = request.form['description']

            filename = "Img"+str(round(time.time()))+".jpg"
            file.save(os.path.join(app.config['UPLOAD_FOLDER'],filename))
            id = str(random.randint(1000, 9999))
            json = {'id': id,
                    'ProductName': pname,'ProductType':ptype,
                    'Quantity': qty,'Price':price,
                    'Description': description,'FileName':filename}
            db = firestore.client()
            newdb_ref = db.collection('newproduct')
            id = json['id']
            newdb_ref.document(id).set(json)
            msg="New Product Added Success"
        return render_template("adminaddproduct.html", msg=msg, ptypes=ptypes)
    except Exception as e:
        return str(e)

@app.route('/adminadddoctor', methods=['POST','GET'])
def adminadddoctor():
    try:
        print("Add New doctor page")
        msg=""
        if request.method == 'POST':
            fname = request.form['fname']
            lname = request.form['lname']
            uname = request.form['uname']
            pwd = request.form['pwd']
            email = request.form['email']
            phnum = request.form['phnum']
            address = request.form['address']
            id = str(round(time.time()))
            #encMessage = fernet.encrypt(pwd.encode())
            encode = base64.b64encode(pwd.encode("utf-8"))
            json = {'id': id,
                    'FirstName': fname,'LastName':lname,
                    'UserName': uname,'Password':encode,
                    'EmailId': email,'PhoneNumber':phnum,
                    'Address': address}
            db = firestore.client()
            newdb_ref = db.collection('newdoctor')
            id = json['id']
            newdb_ref.document(id).set(json)
            msg="New doctor Added Success"
        return render_template("adminadddoctor.html", msg=msg)
    except Exception as e:
        return str(e)

@app.route('/contact', methods=['POST','GET'])
def contactpage():
    try:
        msg=""
        if request.method == 'POST':
            cname = str(request.form['cname'])# + " " + str(request.form['lname'])
            subject = request.form['subject']
            message = request.form['message']
            email = request.form['email']
            id = str(random.randint(1000, 9999))
            json = {'id': id,
                    'ContactName': cname, 'Subject': subject,
                    'Message': message,
                    'EmailId': email}
            db = firestore.client()
            newdb_ref = db.collection('newcontact')
            id = json['id']
            newdb_ref.document(id).set(json)
            body = "Thank you for contacting us, " + str(cname) + " We will keep in touch with in 24 Hrs"
            receipients = [email]
            send_email(subject,body,recipients=receipients)
            msg = "New Contact Added Success"
        return render_template("contact.html", msg=msg)
    except Exception as e:
        return str(e)

@app.route('/adminviewcustomers', methods=['POST','GET'])
def adminviewusers():
    try:
        db = firestore.client()
        newdata_ref = db.collection('newcustomer')
        newdata = newdata_ref.get()
        data=[]
        for doc in newdata:
            data.append(doc.to_dict())
        print("Users Data " , data)
        return render_template("adminviewcustomers.html", data=data)
    except Exception as e:
        return str(e)

@app.route('/doctorviewcustomers', methods=['POST','GET'])
def doctorviewcustomers():
    try:
        db = firestore.client()
        newdata_ref = db.collection('newcustomer')
        newdata = newdata_ref.get()
        data=[]
        for doc in newdata:
            data.append(doc.to_dict())
        print("Users Data " , data)
        return render_template("doctorviewcustomers.html", data=data)
    except Exception as e:
        return str(e)

@app.route('/doctorviewappointments', methods=['POST','GET'])
def doctorviewappointments():
    try:
        db = firestore.client()
        id=session['userid']
        newdata_ref = db.collection('newappointment')
        newdata = newdata_ref.get()
        data=[]
        for doc in newdata:
            temp=doc.to_dict()
            if(temp['DoctorId']==str(id)):
                data.append(doc.to_dict())
        print("Users Data " , data)
        return render_template("doctorviewappointments.html", data=data)
    except Exception as e:
        return str(e)

@app.route('/adminviewappointments', methods=['POST','GET'])
def adminviewappointments():
    try:
        db = firestore.client()
        newdata_ref = db.collection('newappointment')
        newdata = newdata_ref.get()
        data=[]
        for doc in newdata:
            data.append(doc.to_dict())
        print("Users Data " , data)
        return render_template("adminviewappointments.html", data=data)
    except Exception as e:
        return str(e)

@app.route('/adminviewcart', methods=['POST','GET'])
def adminviewcart():
    try:
        db = firestore.client()
        newdata_ref = db.collection('newaddtocart')
        newdata = newdata_ref.get()
        data=[]
        for doc in newdata:
            data.append(doc.to_dict())
        print("Users Data " , data)
        return render_template("adminviewcart.html", data=data)
    except Exception as e:
        return str(e)

@app.route('/doctorviewproducts', methods=['POST','GET'])
def doctorviewproducts():
    try:
        db = firestore.client()
        newdata_ref = db.collection('newproduct')
        newdata = newdata_ref.get()
        data=[]
        for doc in newdata:
            data.append(doc.to_dict())
        print("Users Data " , data)
        return render_template("doctorviewproducts.html", data=data)
    except Exception as e:
        return str(e)

@app.route('/customerviewproducts', methods=['POST','GET'])
def customerviewproducts():
    try:
        db = firestore.client()
        newdata_ref = db.collection('newproduct')
        newdata = newdata_ref.get()
        data=[]
        for doc in newdata:
            data.append(doc.to_dict())
        print("Users Data " , data)
        return render_template("customerviewproducts.html", data=data)
    except Exception as e:
        return str(e)

@app.route('/adminviewproducts', methods=['POST','GET'])
def adminviewproducts():
    try:
        db = firestore.client()
        newdata_ref = db.collection('newproduct')
        newdata = newdata_ref.get()
        data=[]
        for doc in newdata:
            data.append(doc.to_dict())
        print("Users Data " , data)
        return render_template("adminviewproducts.html", data=data)
    except Exception as e:
        return str(e)

@app.route('/doctorupdatedelivery', methods=['POST','GET'])
def doctorupdatedelivery():
    try:
        id=request.args['id']
        time = datetime.datetime.now()
        now = time.strftime("%m/%d/%y %H:%M:%S")
        db = firestore.client()
        data_ref = db.collection(u'newaddtocart').document(id)
        data_ref.update({u'DeliveryStatus': 'DeliveryDone'})
        data_ref.update({u'DeliveryDate': now})
        return redirect(url_for("doctorviewcart"))
    except Exception as e:
        return str(e)

@app.route('/doctorviewusers', methods=['POST','GET'])
def doctorviewusers():
    try:
        db = firestore.client()
        newdata_ref = db.collection('newcustomer')
        newdata = newdata_ref.get()
        data=[]
        for doc in newdata:
            data.append(doc.to_dict())
        print("Users Data " , data)
        return render_template("doctorviewusers.html", data=data)
    except Exception as e:
        return str(e)

@app.route('/doctorviewinfos', methods=['POST','GET'])
def doctorviewinfos():
    try:
        db = firestore.client()
        newdata_ref = db.collection('newinfo')
        newdata = newdata_ref.get()
        data=[]
        for doc in newdata:
            data.append(doc.to_dict())
        print("Users Data " , data)
        return render_template("doctorviewinfos.html", data=data)
    except Exception as e:
        return str(e)

@app.route('/adminviewdoctors', methods=['POST','GET'])
def adminviewdoctors():
    try:
        db = firestore.client()
        newdata_ref = db.collection('newdoctor')
        newdata = newdata_ref.get()
        data=[]
        for doc in newdata:
            data.append(doc.to_dict())
        print("Users Data " , data)
        return render_template("adminviewdoctors.html", data=data)
    except Exception as e:
        return str(e)

@app.route('/adminviewcontacts', methods=['POST','GET'])
def adminviewcontacts():
    try:
        db = firestore.client()
        newdata_ref = db.collection('newcontact')
        newdata = newdata_ref.get()
        data=[]
        for doc in newdata:
            data.append(doc.to_dict())
        print("Contact Data " , data)
        return render_template("adminviewcontacts.html", data=data)
    except Exception as e:
        return str(e)

@app.route('/adminviewreports', methods=['POST','GET'])
def adminviewreports():
    try:
        db = firestore.client()
        newdata_ref = db.collection('newquery')
        newdata = newdata_ref.get()
        data=[]
        for doc in newdata:
            data.append(doc.to_dict())
        print("Report Data " , data)
        return render_template("adminviewreports.html", data=data)
    except Exception as e:
        return str(e)

@app.route('/adminmainpage')
def adminmainpage():
    try:
        return render_template("adminmainpage.html")
    except Exception as e:
        return str(e)

# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    app.debug = True
    app.run()