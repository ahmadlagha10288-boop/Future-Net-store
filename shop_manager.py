import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import urllib.parse

# --- إعدادات الصفحة ---
st.set_page_config(page_title="Future Net - POS System", layout="wide")

# --- بيانات المحل الثابتة ---
SHOP_NAME = "Future Net"
SHOP_PHONE = "96171499798" 
SHOP_ADDRESS = "القبة - مفرق الأمين - بجانب جامع عائشة"

# --- قاعدة البيانات ---
conn = sqlite3.connect('future_net_data.db', check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS inventory 
             (barcode TEXT PRIMARY KEY, name TEXT, cost REAL, price REAL, quantity INTEGER, min_limit INTEGER DEFAULT 3)''')
c.execute('''CREATE TABLE IF NOT EXISTS sales 
             (id INTEGER PRIMARY KEY AUTOINCREMENT, items_list TEXT, total_price REAL, total_profit REAL, sale_date TEXT)''')
conn.commit()

# --- دالة إنشاء فاتورة واتساب الاحترافية ---
def generate_wa_invoice(cart, total_usd, rate):
    invoice_text = f"✨ *فاتورة شراء من {SHOP_NAME}* ✨\n"
    invoice_text += f"📍 {SHOP_ADDRESS}\n"
    invoice_text += f"📅 التاريخ: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
    invoice_text += "--------------------------------\n"
    for item in cart:
        invoice_text += f"🔹 {item['name']} - ${item['price']}\n"
    invoice_text += "--------------------------------\n"
    invoice_text += f"💰 *المجموع:* ${total_usd:.2f}\n"
    invoice_text += f"💵 *بالليرة:* {total_usd * rate:,.0f} L.L\n"
    invoice_text += "--------------------------------\n"
    invoice_text += "🙏 شكراً لزيارتكم لـ Future Net، أهلاً وسهلاً بك دائماً!\n"
    invoice_text += f"📞 للتواصل: {SHOP_PHONE}"
    
    encoded_text = urllib.parse.quote(invoice_text)
    return f"https://wa.me/?text={encoded_text}"

# --- القائمة الجانبية ---
st.sidebar.title(f"🚀 {SHOP_NAME} Admin")
rate = st.sidebar.number_input("سعر صرف $ اليوم:", min_value=1, value=89500)
menu = st.sidebar.radio("القائمة:", ["🛒 نقطة البيع", "📦 المستودع والجرد", "📊 التقارير والأرباح"])

# --- 1. نقطة البيع ---
if menu == "🛒 نقطة البيع":
    st.header(f"🛒 فاتورة جديدة - {SHOP_NAME}")
    
    if 'cart' not in st.session_state: st.session_state.cart = []

    search_barcode = st.text_input("سكان الباركود (Barcode):", key="pos_scan")
    if search_barcode:
        c.execute("SELECT * FROM inventory WHERE barcode=?", (search_barcode,))
        item = c.fetchone()
        if item and item[4] > 0:
            st.session_state.cart.append({"barcode": item[0], "name": item[1], "price": item[3], "cost": item[2]})
            st.rerun()
        elif item: st.error("عذراً، الكمية نفذت!")
        else: st.warning("هذا المنتج غير مسجل في المستودع.")

    if st.session_state.cart:
        st.subheader("📋 محتويات الفاتورة")
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
            st.success("تم تسجيل المبيع بنجاح!")
            st.link_button("📲 إرسال الفاتورة عبر واتساب للزبون", wa_link)
            
            if st.button("بدء فاتورة جديدة"):
                st.session_state.cart = []
                st.rerun()
                
        if c2.button("🗑️ إلغاء الفاتورة", use_container_width=True):
            st.session_state.cart = []
            st.rerun()

# --- 2. المستودع والجرد ---
elif menu == "📦 المستودع والجرد":
    st.header(f"📦 جرد مستودع {SHOP_NAME}")
    
    with st.expander("➕ إضافة صنف جديد للمحل"):
        with st.form("add_item"):
            b = st.text_input("الباركود (سكان)")
            n = st.text_input("اسم المنتج")
            cp = st.number_input("سعر التكلفة (رأس المال) $")
            sp = st.number_input("سعر المبيع للزبون $")
            q = st.number_input("الكمية المتوفرة", step=1)
            if st.form_submit_button("إضافة للمخزن"):
                c.execute("INSERT OR REPLACE INTO inventory (barcode, name, cost, price, quantity) VALUES (?, ?, ?, ?, ?)", (b,n,cp,sp,q))
                conn.commit()
                st.success("تمت الإضافة!")
                st.rerun()

    st.subheader("📋 البضاعة الموجودة حالياً")
    df_inv = pd.read_sql_query("SELECT * FROM inventory", conn)
    st.dataframe(df_inv, use_container_width=True)

# --- 3. التقارير والأرباح ---
else:
    st.header(f"📊 تقارير مبيعات {SHOP_NAME}")
    df_sales = pd.read_sql_query("SELECT * FROM sales", conn)
    if not df_sales.empty:
        st.metric("صافي أرباح المحل (Profit)", f"${df_sales['total_profit'].sum():.2f}")
        st.subheader("تفاصيل مبيعات اليوم")
        st.dataframe(df_sales, use_container_width=True)
    else:
        st.info("لا توجد مبيعات مسجلة حالياً.")
