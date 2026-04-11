import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import urllib.parse

# --- إعدادات الصفحة ---
st.set_page_config(page_title="Future Net Ultimate PRO", layout="wide")

# --- بيانات المحل ---
SHOP_NAME = "Future Net"
SHOP_PHONE = "96171499798" 
SHOP_ADDRESS = "القبة - مفرق الأمين - بجانب جامع عائشة"

# --- قاعدة البيانات ---
conn = sqlite3.connect('future_net_v3.db', check_same_thread=False)
c = conn.cursor()
# جداول: المستودع، المبيعات، الديون، المصاريف
c.execute('CREATE TABLE IF NOT EXISTS inventory (barcode TEXT PRIMARY KEY, name TEXT, cost REAL, price REAL, quantity INTEGER)')
c.execute('CREATE TABLE IF NOT EXISTS sales (id INTEGER PRIMARY KEY AUTOINCREMENT, items TEXT, total REAL, profit REAL, date TEXT)')
c.execute('CREATE TABLE IF NOT EXISTS debts (id INTEGER PRIMARY KEY AUTOINCREMENT, customer TEXT, amount REAL, date TEXT, status TEXT)')
c.execute('CREATE TABLE IF NOT EXISTS expenses (id INTEGER PRIMARY KEY AUTOINCREMENT, reason TEXT, amount REAL, date TEXT)')
conn.commit()

# --- دالة واتساب ---
def generate_wa_invoice(cart, total, rate):
    text = f"✨ *فاتورة {SHOP_NAME}* ✨\n📍 {SHOP_ADDRESS}\n📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}\n--------------------------\n"
    for i in cart: text += f"🔹 {i['name']} - ${i['price']}\n"
    text += f"--------------------------\n💰 المجموع: ${total:.2f}\n💵 بالليرة: {total*rate:,.0f} L.L\n🙏 شكراً لزيارتكم!"
    return f"https://wa.me/?text={urllib.parse.quote(text)}"

# --- القائمة الجانبية ---
st.sidebar.title(f"🚀 {SHOP_NAME}")
rate = st.sidebar.number_input("سعر صرف اليوم:", value=89500)
menu = st.sidebar.radio("القائمة الرئيسية:", ["🛒 نقطة البيع", "📦 المستودع والجرد", "📒 دفتر الديون", "💸 المصاريف", "📈 الأرباح والملفات"])

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
        elif item: st.error("نفذت الكمية!")
        else: st.warning("المنتج غير موجود")

    if st.session_state.cart:
        df = pd.DataFrame(st.session_state.cart)
        st.table(df[['name', 'price']])
        total = df['price'].sum()
        
        pay_type = st.radio("طريقة الدفع:", ["كاش (Cash)", "دين (Debt)"])
        
        if st.button("✅ إتمام العملية"):
            items_names = ", ".join([i['name'] for i in st.session_state.cart])
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            if pay_type == "كاش (Cash)":
                c.execute("INSERT INTO sales (items, total, profit, date) VALUES (?, ?, ?, ?)",
                          (items_names, total, total - df['cost'].sum(), now))
            else:
                cust_name = st.text_input("اسم الزبون صاحب الدين:")
                if cust_name:
                    c.execute("INSERT INTO debts (customer, amount, date, status) VALUES (?, ?, ?, ?)",
                              (cust_name, total, now, "غير مدفوع"))
                else: st.error("يرجى كتابة اسم الزبون للدين!"); st.stop()

            for i in st.session_state.cart:
                c.execute("UPDATE inventory SET quantity = quantity - 1 WHERE barcode=?", (i['barcode'],))
            conn.commit()
            st.link_button("📲 إرسال فاتورة واتساب", generate_wa_invoice(st.session_state.cart, total, rate))
            st.session_state.cart = []
            st.success("تم الحفظ بنجاح!")

# --- 2. المستودع ---
elif menu == "📦 المستودع والجرد":
    st.header("📦 إدارة المخزون")
    # تنبيه النواقص
    c.execute("SELECT name, quantity FROM inventory WHERE quantity < 3")
    low_stock = c.fetchall()
    for p in low_stock: st.warning(f"⚠️ انتبه: {p[0]} باقي منه {p[1]} قطع فقط!")

    with st.form("add_item"):
        col1, col2 = st.columns(2)
        b = col1.text_input("الباركود")
        n = col2.text_input("اسم المنتج")
        cp = col1.number_input("التكلفة $")
        sp = col2.number_input("المبيع $")
        q = st.number_input("الكمية", step=1)
        if st.form_submit_button("حفظ"):
            c.execute("INSERT OR REPLACE INTO inventory VALUES (?,?,?,?,?)", (b,n,cp,sp,q))
            conn.commit(); st.rerun()
    st.dataframe(pd.read_sql_query("SELECT * FROM inventory", conn), use_container_width=True)

# --- 3. دفتر الديون ---
elif menu == "📒 دفتر الديون":
    st.header("📒 سجل الديون الخارجية")
    df_debts = pd.read_sql_query("SELECT * FROM debts WHERE status='غير مدفوع'", conn)
    st.subheader(f"إجمالي الديون المطلوبة منك: ${df_debts['amount'].sum():.2f}")
    st.table(df_debts)
    
    with st.expander("✅ تحصيل دين (تم الدفع)"):
        d_id = st.number_input("رقم الدين (ID):", step=1)
        if st.button("تأكيد الدفع"):
            c.execute("UPDATE debts SET status='تم الدفع' WHERE id=?", (d_id,))
            conn.commit(); st.rerun()

# --- 4. المصاريف ---
elif menu == "💸 المصاريف":
    st.header("💸 مصاريف المحل اليومية")
    with st.form("exp"):
        reason = st.text_input("سبب المصروف (إيجار، إنترنت، مولد...)")
        amt = st.number_input("المبلغ $")
        if st.form_submit_button("تسجيل المصروف"):
            c.execute("INSERT INTO expenses (reason, amount, date) VALUES (?, ?, ?)", 
                      (reason, amt, datetime.now().strftime('%Y-%m-%d')))
            conn.commit(); st.rerun()
    st.table(pd.read_sql_query("SELECT * FROM expenses", conn))

# --- 5. الأرباح والملفات ---
else:
    st.header("📈 التقارير المالية")
    sales_profit = pd.read_sql_query("SELECT SUM(profit) FROM sales", conn).iloc[0,0] or 0
    total_expenses = pd.read_sql_query("SELECT SUM(amount) FROM expenses", conn).iloc[0,0] or 0
    
    col1, col2, col3 = st.columns(3)
    col1.metric("أرباح المبيعات", f"${sales_profit:.2f}")
    col2.metric("إجمالي المصاريف", f"-${total_expenses:.2f}")
    col3.metric("صافي الربح الفعلي", f"${sales_profit - total_expenses:.2f}", delta_color="normal")

    st.divider()
    st.subheader("📁 إدارة الملفات (Backup)")
    df_inv = pd.read_sql_query("SELECT * FROM inventory", conn)
    st.download_button("تحميل نسخة المستودع Excel", df_inv.to_csv().encode('utf-8-sig'), "future_net_stock.csv")
