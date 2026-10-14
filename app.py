import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, date
import os

# Configuración de página optimizada para celulares
st.set_page_config(
    page_title="Mi Tiendita - Control Diario",
    page_icon="🏪",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Estilos CSS Mobile-First para mejorar la usabilidad en pantallas táctiles
st.markdown("""
<style>
    /* Optimización táctil y espaciado para móviles */
    .stButton>button {
        width: 100%;
        border-radius: 12px;
        height: 3.2rem;
        font-size: 1.15rem;
        font-weight: 600;
        margin-top: 0.5rem;
        margin-bottom: 0.5rem;
        transition: transform 0.1s ease-in-out;
    }
    .stButton>button:active {
        transform: scale(0.98);
    }
    
    /* Tarjetas de métricas estilizadas */
    div[data-testid="stMetric"] {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        padding: 12px 14px;
        border-radius: 14px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    
    /* Inputs táctiles más accesibles */
    div[data-baseweb="input"] {
        border-radius: 10px;
    }
    div[data-baseweb="select"] {
        border-radius: 10px;
    }
    
    /* Títulos compactos para pantalla móvil */
    h1 {
        font-size: 1.85rem !important;
        margin-bottom: 0.2rem !important;
    }
    h2, h3 {
        font-size: 1.35rem !important;
    }
    
    .badge-pill {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 9999px;
        font-size: 0.85rem;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

DB_PATH = "tienda.db"
CATEGORIAS = ["Refrescos", "Sabritas", "Galletas"]

# --- FUNCIONES DE BASE DE DATOS (SQLite) ---
def init_db():
    """Inicializa la base de datos y la tabla de movimientos."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS movimientos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TEXT NOT NULL,
            tipo TEXT NOT NULL,
            categoria TEXT NOT NULL,
            cantidad INTEGER NOT NULL,
            monto REAL NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def registrar_movimiento(tipo, categoria, cantidad, monto, fecha_mov):
    """Guarda un nuevo movimiento (Venta o Compra)."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO movimientos (fecha, tipo, categoria, cantidad, monto)
        VALUES (?, ?, ?, ?, ?)
    """, (fecha_mov.strftime("%Y-%m-%d"), tipo, categoria, int(cantidad), float(monto)))
    conn.commit()
    conn.close()

def obtener_movimientos(fecha_filtro=None):
    """Obtiene movimientos, opcionalmente filtrados por fecha."""
    conn = sqlite3.connect(DB_PATH)
    if fecha_filtro:
        query = "SELECT id, fecha, tipo, categoria, cantidad, monto, timestamp FROM movimientos WHERE fecha = ? ORDER BY id DESC"
        df = pd.read_sql_query(query, conn, params=(fecha_filtro.strftime("%Y-%m-%d"),))
    else:
        query = "SELECT id, fecha, tipo, categoria, cantidad, monto, timestamp FROM movimientos ORDER BY id DESC"
        df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def eliminar_movimiento(id_mov):
    """Elimina un movimiento por su ID."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM movimientos WHERE id = ?", (id_mov,))
    conn.commit()
    conn.close()

# Inicializar BD
init_db()

# --- CABECERA DE LA APP ---
col_head1, col_head2 = st.columns([4, 1])
with col_head1:
    st.markdown("### 🏪 Tienda de Abarrotes")
    st.caption(f"📅 Fecha actual: **{date.today().strftime('%d/%m/%Y')}**")

# Selector de pestañas móvil
tab_venta, tab_compra, tab_metricas, tab_historial = st.tabs([
    "💵 Vender", 
    "📦 Comprar", 
    "📊 Métricas",
    "📋 Historial"
])

# ==========================================
# PESTAÑA 1: REGISTRAR VENTAS
# ==========================================
with tab_venta:
    st.markdown("#### 💰 Nueva Venta")
    with st.form("form_venta", clear_on_submit=True):
        cat_venta = st.selectbox(
            "Categoría del producto:",
            options=CATEGORIAS,
            key="cat_v"
        )
        
        cant_venta = st.number_input(
            "Cantidad de piezas vendidas:",
            min_value=1,
            value=1,
            step=1,
            key="cant_v"
        )
        
        monto_venta = st.number_input(
            "Total cobrado / Ingreso ($):",
            min_value=0.0,
            value=0.0,
            step=5.0,
            format="%.2f",
            help="Ingresa el monto total en pesos recibido por esta venta",
            key="monto_v"
        )
        
        submitted_v = st.form_submit_button("✅ Guardar Venta", type="primary")
        
        if submitted_v:
            if monto_venta <= 0:
                st.error("⚠️ Por favor ingresa un monto válido mayor a $0.")
            else:
                registrar_movimiento("Venta", cat_venta, cant_venta, monto_venta, date.today())
                st.success(f"¡Venta registrada! +${monto_venta:,.2f} en {cat_venta} ({cant_venta} pza)")
                st.rerun()

# ==========================================
# PESTAÑA 2: REGISTRAR COMPRAS / GASTOS
# ==========================================
with tab_compra:
    st.markdown("#### 🛒 Registrar Compra / Gasto")
    st.caption("Anota el surtido o compra de mercancía para tu inventario.")
    
    with st.form("form_compra", clear_on_submit=True):
        cat_compra = st.selectbox(
            "Categoría de la mercancía:",
            options=CATEGORIAS,
            key="cat_c"
        )
        
        cant_compra = st.number_input(
            "Cantidad de piezas surtidas:",
            min_value=1,
            value=1,
            step=1,
            key="cant_c"
        )
        
        monto_compra = st.number_input(
            "Costo total pagado al proveedor ($):",
            min_value=0.0,
            value=0.0,
            step=10.0,
            format="%.2f",
            help="Ingresa el costo total que pagaste por el producto",
            key="monto_c"
        )
        
        submitted_c = st.form_submit_button("📥 Guardar Compra", type="primary")
        
        if submitted_c:
            if monto_compra <= 0:
                st.error("⚠️ Por favor ingresa un costo válido mayor a $0.")
            else:
                registrar_movimiento("Compra/Gasto", cat_compra, cant_compra, monto_compra, date.today())
                st.success(f"¡Compra registrada! -${monto_compra:,.2f} en {cat_compra} ({cant_compra} pza)")
                st.rerun()

# ==========================================
# PESTAÑA 3: MÉTRICAS Y RESUMEN DEL DÍA
# ==========================================
with tab_metricas:
    col_t, col_f = st.columns([2, 1])
    with col_t:
        st.markdown("#### 📈 Resumen del Día")
    with col_f:
        fecha_seleccionada = st.date_input("Fecha:", value=date.today(), label_visibility="collapsed")
    
    # Obtener datos del día seleccionado
    df_dia = obtener_movimientos(fecha_filtro=fecha_seleccionada)
    
    if df_dia.empty:
        st.info(f"No hay movimientos registrados para el {fecha_seleccionada.strftime('%d/%m/%Y')}.")
        total_ventas = 0.0
        total_compras = 0.0
        ganancia_neta = 0.0
    else:
        ventas_df = df_dia[df_dia["tipo"] == "Venta"]
        compras_df = df_dia[df_dia["tipo"] == "Compra/Gasto"]
        
        total_ventas = ventas_df["monto"].sum() if not ventas_df.empty else 0.0
        total_compras = compras_df["monto"].sum() if not compras_df.empty else 0.0
        ganancia_neta = total_ventas - total_compras

    # Panel de métricas principales
    m1, m2 = st.columns(2)
    with m1:
        st.metric(
            label="💵 Total Vendido", 
            value=f"${total_ventas:,.2f}"
        )
    with m2:
        st.metric(
            label="🛒 Total Comprado", 
            value=f"${total_compras:,.2f}"
        )
    
    # Métrica destacada de Ganancia Neta
    delta_color = "normal" if ganancia_neta >= 0 else "inverse"
    st.metric(
        label="🎯 Ganancia Neta del Día",
        value=f"${ganancia_neta:,.2f}",
        delta=f"{'+' if ganancia_neta >= 0 else ''}${ganancia_neta:,.2f}",
        delta_color=delta_color
    )
    
    # Desglose por categoría si hay ventas o compras
    if not df_dia.empty:
        st.divider()
        st.markdown("##### 📦 Desglose por Categoría")
        
        resumen_cat = []
        for cat in CATEGORIAS:
            v_sub = df_dia[(df_dia["tipo"] == "Venta") & (df_dia["categoria"] == cat)]
            c_sub = df_dia[(df_dia["tipo"] == "Compra/Gasto") & (df_dia["categoria"] == cat)]
            
            piezas_v = int(v_sub["cantidad"].sum()) if not v_sub.empty else 0
            monto_v = float(v_sub["monto"].sum()) if not v_sub.empty else 0.0
            
            piezas_c = int(c_sub["cantidad"].sum()) if not c_sub.empty else 0
            monto_c = float(c_sub["monto"].sum()) if not c_sub.empty else 0.0
            
            resumen_cat.append({
                "Categoría": cat,
                "Vendidas": f"{piezas_v} pz",
                "Venta ($)": f"${monto_v:,.2f}",
                "Compradas": f"{piezas_c} pz",
                "Gasto ($)": f"${monto_c:,.2f}"
            })
            
        st.dataframe(pd.DataFrame(resumen_cat), hide_index=True, use_container_width=True)

# ==========================================
# PESTAÑA 4: HISTORIAL Y GESTIÓN
# ==========================================
with tab_historial:
    st.markdown("#### 📋 Movimientos de Hoy")
    df_hoy = obtener_movimientos(fecha_filtro=date.today())
    
    if df_hoy.empty:
        st.caption("Aún no has registrado movimientos hoy.")
    else:
        st.write(f"Total registros hoy: **{len(df_hoy)}**")
        for _, row in df_hoy.iterrows():
            icono = "💵" if row["tipo"] == "Venta" else "🛒"
            color = "#16a34a" if row["tipo"] == "Venta" else "#dc2626"
            
            with st.container():
                col_info, col_del = st.columns([5, 1])
                with col_info:
                    st.markdown(
                        f"**{icono} {row['tipo']} - {row['categoria']}**  \n"
                        f"Cantidad: `{row['cantidad']} pza` | Monto: <span style='color:{color}; font-weight:700;'>${row['monto']:,.2f}</span>",
                        unsafe_allow_html=True
                    )
                with col_del:
                    if st.button("🗑️", key=f"del_{row['id']}", help="Eliminar este registro"):
                        eliminar_movimiento(row['id'])
                        st.toast("Movimiento eliminado correctamente")
                        st.rerun()
                st.markdown("<hr style='margin: 4px 0 10px 0; border: none; border-top: 1px dashed #e2e8f0;'>", unsafe_allow_html=True)
