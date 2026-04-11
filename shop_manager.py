import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import urllib.parse
from streamlit_camera_input_live import camera_input_live
from PIL import Image

# --- إعدادات الصفحة وقاعدة البيانات ---
st.set_page_config(page_title="Future Net - PRO POS", layout="wide")

# (نفس بيانات المحل الثابتة)
SHOP_NAME = "Future Net"
SHOP_PHONE = "96171499798" 
SHOP_ADDRESS = "القبة - مفرق الأمين - بجانب جامع عائشة"

conn = sqlite3.connect('future_net_pro.db', check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS inventory 
             (barcode TEXT PRIMARY KEY, name TEXT, cost REAL, price REAL, quantity INTEGER, min_limit INTEGER DEFAULT 3)''')
c.execute('''CREATE TABLE IF NOT EXISTS sales 
             (id INTEGER PRIMARY KEY AUTOINCREMENT, items_list TEXT, total_price REAL, total_profit REAL, sale_date TEXT)''')
conn.commit()

# --- دالة فاتورة واتساب (نفسها) ---
def generate_wa_invoice(cart, total_usd, rate):
    invoice_text = f"✨ *فاتورة شراء من {SHOP_NAME}* ✨\n📍 {SHOP_ADDRESS}\n📅 التاريخ: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n--------------------------------\n"
    for item in cart:
        invoice_text += f"🔹 {item['name']} - ${item['price']}\n"
    invoice_text += "--------------------------------\n"
    invoice_text += f"💰 *المجموع:* ${total_usd:.2f}\n💵 *بالليرة:* {total_usd * rate:,.0f} L.L\n--------------------------------\n"
    invoice_text += "🙏 شكراً لزيارتكم، أهلاً وسهلاً بك دائماً!\n📞 {SHOP_PHONE}"
    return f"https://wa.me/?text={urllib.parse.quote(invoice_text)}"

# --- القائمة الجانبية ---
st.sidebar.title(f"🚀 {SHOP_NAME} PRO")
rate = st.sidebar.number_input("سعر صرف الليرة:", min_value=1, value=89500)
menu = st.sidebar.radio("القائمة:", ["🛒 نقطة البيع (كاميرا)", "📦 المستودع والجرد", "📊 التقارير"])

# --- 1. نقطة البيع الاحترافية (مع الكاميرا) ---
if menu == "🛒 نقطة البيع (كاميرا)":
    st.header(f"🛒 فاتورة جديدة - {SHOP_NAME}")
    
    if 'cart' not in st.session_state: st.session_state.cart = []

    # 🚨 الإضافة الاحترافية: الكاميرا المباشرة
    st.subheader("🤳 سكان للباركود")
    st.info("وجه كاميرا الأيفون نحو باركود القطعة...")
    
    # حقل الكاميرا المباشر
    scanned_image = camera_input_live(key="barcode_cam")
    
    # المتغير الذي سيحمل رقم الباركود
    barcode_val = ""

    # إذا لقطت الكاميرا صورة، نقوم بتحليلها فوراً
    if scanned_image:
        # ملاحظة تقنية: مكتبة camera_input_live بترجع الصورة. 
        # لتحويل الصورة لباركود حقيقي، نحتاج مكتبة (pyzbar) وهي صعبة جداً على الـ Deploy في Streamlit.
        # الحل الاحترافي المتاح ( workaround ): نستخدم ميزة "الأيفون المدمجة" بس بشكل أسرع.
        
        # لعرض الصورة الملتقطة للتأكد
        st.image(scanned_image, caption="تم لقط الصورة، عم جرب سحب النص منها...", width=300)
        st.warning("عفواً، ميزة تحليل الباركود من الصورة مباشرة غير مدعومة بالكامل على الـ Cloud للـ Streamlit. استخدم طريقة الأيفون (Scan Text) المدمجة بالكيبورد هي الأسرع حالياً.")

    # حقل النص العادي (احتياطي)
    search_barcode = st.text_input("أو اكتب الباركود يدوياً:", key="pos_scan_text")
    
    # البحث بالاسم (إذا الباركود ممسوح)
    search_name = st.text_input("أو ابحث باسم المنتج:", key="name_search")

    # تحديد أي طريقة بحث استخدمت
    barcode_to_process = search_barcode if search_barcode else barcode_val

    # (نفس كود معالجة البيع القديم)
    if barcode_to_process or search_name:
        query = ""
        param = ""
        if barcode_to_process:
            query = "SELECT * FROM inventory WHERE barcode=?"
            param = (barcode_to_process,)
        elif search_name:
            query = "SELECT * FROM inventory WHERE name LIKE ?"
            param = (f"%{search_name}%",)
            
        c.execute(query, param)
        item = c.fetchone()
        
        if item and item[4] > 0:
            st.session_state.cart.append({"barcode": item[0], "name": item[1], "price": item[3], "cost": item[2]})
            st.rerun()
        elif item: st.error("نفذت الكمية!")
        elif barcode_to_process or search_name: st.warning("المنتج غير موجود.")

    # (عرض الفاتورة وإتمام العملية - نفسه)
    if st.session_state.cart:
        st.subheader("📋 الفاتورة الحالية")
        df_cart = pd.DataFrame(st.session_state.cart)
        st.table(df_cart[['name', 'price']])
        total_sum = df_cart['price'].sum()
        total_cost = df_cart['cost'].sum()
        
        col_res1, col_res2 = st.columns(2)
        col_res1.metric("الإجمالي USD", f"${total_sum:.2f}")
        col_res2.metric("الإجمالي L.L", f"{total_sum * rate:,.0f}")
        
        c1, c2 = st.columns(2)
        if c1.button("✅ إتمام العملية", use_container_width=True):
            profit = total_sum - total_cost
            items_names = ", ".join([i['name'] for i in st.session_state.cart])
            c.execute("INSERT INTO sales (items_list, total_price, total_profit, sale_date) VALUES (?, ?, ?, ?)",
                      (items_names, total_sum, profit, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
            for item in st.session_state.cart:
                c.execute("UPDATE inventory SET quantity = quantity - 1 WHERE barcode=?", (item['barcode'],))
            conn.commit()
            
            wa_link = generate_wa_invoice(st.session_state.cart, total_sum, rate)
            st.success("تم تسجيل البيع بنجاح!")
            st.link_button("📲 إرسال الفاتورة عبر واتساب", wa_link)
            if st.button("بدء فاتورة جديدة"):
                st.session_state.cart = []
                st.rerun()
                
        if c2.button("🗑️ إلغاء الفاتورة", use_container_width=True):
            st.session_state.cart = []
            st.rerun()

# (باقي كود المستودع والتقارير - نفسه)
elif menu == "📦 المستودع والجرد":
    st.header(f"📦 جرد مستودع {SHOP_NAME}")
    with st.expander("➕ إضافة صنف جديد للمحل"):
        with st.form("add_item"):
            b = st.text_input("الباركود (سكان)")
            n = st.text_input("اسم المنتج")
            cp = st.number_input("سعر التكلفة $")
            sp = st.number_input("سعر المبيع $")
            q = st.number_input("الكمية المتوفرة", step=1)
            if st.form_submit_button("إضافة للمخزن"):
                c.execute("INSERT OR REPLACE INTO inventory (barcode, name, cost, price, quantity) VALUES (?, ?, ?, ?, ?)", (b,n,cp,sp,q))
                conn.commit()
                st.success("تمت الإضافة!")
                st.rerun()
    st.dataframe(pd.read_sql_query("SELECT * FROM inventory", conn), use_container_width=True)

else:
    st.header(f"📊 تقارير مبيعات {SHOP_NAME}")
    df_sales = pd.read_sql_query("SELECT * FROM sales", conn)
    if not df_sales.empty:
        st.metric("صافي الأرباح (Profit)", f"${df_sales['total_profit'].sum():.2f}")
        st.dataframe(df_sales, use_container_width=True)
    else:
        st.info("لا توجد مبيعات حالياً.")
