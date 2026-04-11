import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import urllib.parse

# --- إعدادات الصفحة ---
st.set_page_config(page_title="Future Net Ultimate", layout="wide")

# --- بيانات المحل ---
SHOP_NAME = "Future Net"
SHOP_PHONE = "96171499798" 
SHOP_ADDRESS = "القبة - مفرق الأمين - بجانب جامع عائشة"

# --- قاعدة البيانات ---
conn = sqlite3.connect('future_net_final.db', check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS inventory 
             (barcode TEXT PRIMARY KEY, name TEXT, cost REAL, price REAL, quantity INTEGER)''')
c.execute('''CREATE TABLE IF NOT EXISTS sales 
             (id INTEGER PRIMARY KEY AUTOINCREMENT, items_list TEXT, total_price REAL, total_profit REAL, sale_date TEXT)''')
conn.commit()

# --- دالة واتساب ---
def generate_wa_invoice(cart, total_usd, rate):
    text = f"✨ *فاتورة Future Net* ✨\n📍 {SHOP_ADDRESS}\n📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
    text += "--------------------------\n"
    for i in cart: text += f"🔹 {i['name']} - ${i['price']}\n"
    text += "--------------------------\n"
    text += f"💰 المجموع: ${total_usd:.2f}\n💵 بالليرة: {total_usd * rate:,.0f} L.L\n"
    text += "🙏 شكراً لزيارتكم!\n"
    return f"https://wa.me/?text={urllib.parse.quote(text)}"

# --- القائمة الجانبية ---
st.sidebar.title(f"🚀 {SHOP_NAME}")
rate = st.sidebar.number_input("سعر الصرف اليوم:", value=89500)
menu = st.sidebar.radio("انتقل إلى:", ["🛒 نقطة البيع", "📦 المستودع", "📊 الأرباح", "📁 إدارة الملفات"])

# --- 1. نقطة البيع ---
if menu == "🛒 نقطة البيع":
    st.header("🛒 فاتورة بيع جديدة")
    if 'cart' not in st.session_state: st.session_state.cart = []
    
    barcode = st.text_input("سكان للباركود (Scan):")
    if barcode:
        c.execute("SELECT * FROM inventory WHERE barcode=?", (barcode,))
        item = c.fetchone()
        if item and item[4] > 0:
            st.session_state.cart.append({"barcode":item[0], "name":item[1], "price":item[3], "cost":item[2]})
            st.rerun()
        elif item: st.error("الكمية نافذة!")
        else: st.warning("المنتج غير معرف")

    if st.session_state.cart:
        df = pd.DataFrame(st.session_state.cart)
        st.table(df[['name', 'price']])
        total = df['price'].sum()
        if st.button("✅ إنهاء المبيع واستخراج الفاتورة"):
            items = ", ".join([i['name'] for i in st.session_state.cart])
            c.execute("INSERT INTO sales (items_list, total_price, total_profit, sale_date) VALUES (?, ?, ?, ?)",
                      (items, total, total - df['cost'].sum(), datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
            for i in st.session_state.cart:
                c.execute("UPDATE inventory SET quantity = quantity - 1 WHERE barcode=?", (i['barcode'],))
            conn.commit()
            st.link_button("📲 إرسال واتساب", generate_wa_invoice(st.session_state.cart, total, rate))
            st.session_state.cart = []

# --- 2. المستودع ---
elif menu == "📦 المستودع":
    st.header("📦 إدارة المخزون")
    with st.form("add"):
        col1, col2 = st.columns(2)
        b = col1.text_input("الباركود")
        n = col2.text_input("اسم المنتج")
        cp = col1.number_input("التكلفة ($)")
        sp = col2.number_input("المبيع ($)")
        q = st.number_input("الكمية الجاهزة", step=1)
        if st.form_submit_button("حفظ الصنف"):
            c.execute("INSERT OR REPLACE INTO inventory VALUES (?,?,?,?,?)", (b,n,cp,sp,q))
            conn.commit(); st.success("تم الحفظ"); st.rerun()
    st.dataframe(pd.read_sql_query("SELECT * FROM inventory", conn), use_container_width=True)

# --- 3. الأرباح ---
elif menu == "📊 الأرباح":
    st.header("📈 كشف الأرباح")
    df_s = pd.read_sql_query("SELECT * FROM sales", conn)
    st.metric("إجمالي الربح الصافي", f"${df_s['total_profit'].sum():.2f}")
    st.dataframe(df_s, use_container_width=True)

# --- 4. إدارة الملفات (File Manager) ---
else:
    st.header("📁 مدير البيانات والملفات")
    
    # تصدير البيانات لـ Excel
    st.subheader("📥 تصدير (Backup)")
    col_a, col_b = st.columns(2)
    
    df_inv = pd.read_sql_query("SELECT * FROM inventory", conn)
    df_sal = pd.read_sql_query("SELECT * FROM sales", conn)
    
    col_a.download_button("تحميل جرد المستودع (Excel)", df_inv.to_csv(index=False).encode('utf-8-sig'), "inventory_backup.csv", "text/csv")
    col_b.download_button("تحميل سجل المبيعات (Excel)", df_sal.to_csv(index=False).encode('utf-8-sig'), "sales_backup.csv", "text/csv")
    
    st.divider()
    
    # منطقة الخطر (مسح البيانات)
    st.subheader("⚠️ منطقة الخطر (Danger Zone)")
    password = st.text_input("أدخل كلمة سر المدير للمسح:", type="password")
    
    if password == "1234": # غير كلمة السر هنا
        if st.button("🗑️ مسح كافة المبيعات"):
            c.execute("DELETE FROM sales")
            conn.commit()
            st.warning("تم تصدير سجل المبيعات للصفر!")
            
        if st.button("🚨 مسح المستودع بالكامل"):
            c.execute("DELETE FROM inventory")
            conn.commit()
            st.error("تم مسح كافة بضائع المستودع!")
