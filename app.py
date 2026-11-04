import streamlit as st
import pandas as pd
from datetime import datetime, date
import requests
import json

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
    
    .card-deudor {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-left: 5px solid #ef4444;
        padding: 14px;
        border-radius: 12px;
        margin-bottom: 12px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    }
</style>
""", unsafe_allow_html=True)

# URL de la API de Google Apps Script vinculada a tu Google Sheet
GSHEET_API_URL = "https://script.google.com/macros/s/AKfycbxvuRGFjjPaKunAc76G_UbMF_Kk3PLqTEvcupVuoz28OUMZYNFY-bwLi6yBOLKDpTAP/exec"
CATEGORIAS = ["Refrescos", "Sabritas", "Galletas"]

# --- FUNCIONES DE CONEXIÓN CON GOOGLE SHEETS ---

def fetch_all_data():
    """Descarga los datos completos desde Google Sheets vía Apps Script."""
    try:
        resp = requests.get(f"{GSHEET_API_URL}?action=getAll", timeout=12)
        if resp.status_code == 200:
            return resp.json()
    except Exception as e:
        st.error(f"Error conectando con Google Sheets: {e}")
    return {"movimientos": [], "deudores": [], "movimientos_fiado": []}

def api_post(payload):
    """Envía un movimiento o actualización a Google Sheets."""
    try:
        resp = requests.post(
            GSHEET_API_URL, 
            data=json.dumps(payload),
            headers={"Content-Type": "application/json"},
            timeout=15
        )
        return resp.status_code == 200
    except Exception as e:
        st.error(f"Error al guardar en Google Sheets: {e}")
        return False

# Cargar datos desde Google Sheets en caché de sesión para agilizar
data_gs = fetch_all_data()

# Preparar DataFrames
df_movimientos_raw = pd.DataFrame(data_gs.get("movimientos", []))
if not df_movimientos_raw.empty:
    df_movimientos_raw["monto"] = pd.to_numeric(df_movimientos_raw["monto"], errors="coerce").fillna(0.0)
    df_movimientos_raw["cantidad"] = pd.to_numeric(df_movimientos_raw["cantidad"], errors="coerce").fillna(0).astype(int)
    # Formato de fecha estándar
    df_movimientos_raw["fecha"] = df_movimientos_raw["fecha"].astype(str).str[:10]

df_deudores_raw = pd.DataFrame(data_gs.get("deudores", []))
if not df_deudores_raw.empty:
    df_deudores_raw["saldo"] = pd.to_numeric(df_deudores_raw["saldo"], errors="coerce").fillna(0.0)
    df_deudores_raw["nombre"] = df_deudores_raw["nombre"].astype(str)

df_hist_fiado_raw = pd.DataFrame(data_gs.get("movimientos_fiado", []))
if not df_hist_fiado_raw.empty:
    df_hist_fiado_raw["monto"] = pd.to_numeric(df_hist_fiado_raw["monto"], errors="coerce").fillna(0.0)

# --- CABECERA DE LA APP ---
col_head1, col_head2 = st.columns([4, 1])
with col_head1:
    st.markdown("### 🏪 Tienda de Abarrotes")
    st.caption(f"📅 Fecha: **{date.today().strftime('%d/%m/%Y')}** | ☁️ *En la nube (Google Sheets)*")
with col_head2:
    if st.button("🔄", help="Recargar datos de Google Sheets"):
        st.rerun()

# Selector de pestañas móvil
tab_venta, tab_compra, tab_deudores, tab_metricas, tab_historial = st.tabs([
    "💵 Vender", 
    "📦 Comprar", 
    "📒 Deudores",
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
                with st.spinner("Guardando en Google Sheets..."):
                    payload = {
                        "action": "addMovimiento",
                        "tipo": "Venta",
                        "categoria": cat_venta,
                        "cantidad": int(cant_venta),
                        "monto": float(monto_venta),
                        "fecha": date.today().strftime("%Y-%m-%d")
                    }
                    if api_post(payload):
                        st.success(f"¡Venta guardada en la nube! +${monto_venta:,.2f} en {cat_venta}")
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
                with st.spinner("Guardando en Google Sheets..."):
                    payload = {
                        "action": "addMovimiento",
                        "tipo": "Compra/Gasto",
                        "categoria": cat_compra,
                        "cantidad": int(cant_compra),
                        "monto": float(monto_compra),
                        "fecha": date.today().strftime("%Y-%m-%d")
                    }
                    if api_post(payload):
                        st.success(f"¡Compra guardada en la nube! -${monto_compra:,.2f} en {cat_compra}")
                        st.rerun()

# ==========================================
# PESTAÑA 3: DEUDORES / LO FIADO
# ==========================================
with tab_deudores:
    st.markdown("#### 📒 Control de Deudores y Fiado")
    
    accion_fiado = st.radio(
        "¿Qué deseas hacer?",
        ["👥 Ver Deudores Activos", "➕ Anotar Fiado", "💳 Registrar Pago"],
        horizontal=True,
        label_visibility="collapsed"
    )
    
    # Filtrar solo deudores con saldo > 0
    if not df_deudores_raw.empty:
        df_activos = df_deudores_raw[df_deudores_raw["saldo"] > 0].sort_values(by="saldo", ascending=False)
    else:
        df_activos = pd.DataFrame()

    total_por_cobrar = df_activos["saldo"].sum() if not df_activos.empty else 0.0
    
    # Métrica resumen del fiado
    m_f1, m_f2 = st.columns(2)
    with m_f1:
        st.metric("Total por Cobrar", f"${total_por_cobrar:,.2f}")
    with m_f2:
        st.metric("Deudores Pendientes", f"{len(df_activos)} personas")
    
    st.divider()

    # --- SECCIÓN 1: VER LISTA DE DEUDORES ACTIVOS ---
    if accion_fiado == "👥 Ver Deudores Activos":
        if df_activos.empty:
            st.success("🎉 ¡Excelente! No hay clientes con deudas pendientes actualmente.")
        else:
            st.caption("Solo se muestran personas con saldo pendiente:")
            for _, row in df_activos.iterrows():
                with st.container():
                    st.markdown(f"""
                    <div class="card-deudor">
                        <div style="display:flex; justify-content:space-between; align-items:center;">
                            <span style="font-size:1.15rem; font-weight:700; color:#1e293b;">👤 {row['nombre']}</span>
                            <span style="font-size:1.25rem; font-weight:800; color:#dc2626;">${row['saldo']:,.2f}</span>
                        </div>
                        <div style="font-size:0.85rem; color:#64748b; margin-top:4px;">
                            📅 Última fecha: {row.get('fecha_actualizacion', 'Reciente')}
                            {f"<br>📝 Notas: {row.get('notas', '')}" if row.get('notas') else ""}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    if st.button(f"💵 Pagar cuenta de {row['nombre']}", key=f"btn_pay_{row['nombre']}"):
                        st.session_state["deudor_a_pagar"] = row["nombre"]
                        st.rerun()

    # --- SECCIÓN 2: ANOTAR NUEVO FIADO O ACUMULAR ---
    elif accion_fiado == "➕ Anotar Fiado":
        st.markdown("##### 📝 Anotar mercancía fiada")
        
        nombres_existentes = df_deudores_raw["nombre"].tolist() if not df_deudores_raw.empty else []
        usar_existente = False
        nombre_cliente = ""
        
        if nombres_existentes:
            modo_nombre = st.radio("Seleccionar cliente:", ["Escribir nuevo", "Elegir existente"], horizontal=True)
            if modo_nombre == "Elegir existente":
                nombre_cliente = st.selectbox("Cliente:", options=sorted(nombres_existentes))
                usar_existente = True
                
        if not usar_existente:
            nombre_cliente = st.text_input("Nombre de la persona:", placeholder="Ej. Doña Carmen, Juan Pérez")
            
        monto_fiado = st.number_input("Monto a fiar ($):", min_value=0.0, value=0.0, step=5.0, format="%.2f")
        notas_fiado = st.text_input("Detalle o productos (opcional):", placeholder="Ej. 2 refrescos y 1 papas")
        fecha_fiado = st.date_input("Fecha:", value=date.today())
        
        if st.button("💾 Guardar en Cuenta Fiada", type="primary"):
            if not nombre_cliente or nombre_cliente.strip() == "":
                st.error("⚠️ Por favor escribe el nombre del cliente.")
            elif monto_fiado <= 0:
                st.error("⚠️ El monto fiado debe ser mayor a $0.")
            else:
                with st.spinner("Guardando en Google Sheets..."):
                    payload = {
                        "action": "addFiado",
                        "nombre": nombre_cliente.strip().title(),
                        "monto": float(monto_fiado),
                        "notas": notas_fiado,
                        "fecha": fecha_fiado.strftime("%Y-%m-%d")
                    }
                    if api_post(payload):
                        st.success(f"¡Anotado! Se sumaron ${monto_fiado:,.2f} a la cuenta de {nombre_cliente.title()}.")
                        st.rerun()

    # --- SECCIÓN 3: REGISTRAR PAGO / SALDAR CUENTA ---
    elif accion_fiado == "💳 Registrar Pago":
        st.markdown("##### 💵 Registrar Abono o Liquidación")
        
        if df_activos.empty:
            st.info("No hay clientes con saldo pendiente en este momento.")
        else:
            nombres_activos = df_activos["nombre"].tolist()
            
            index_defecto = 0
            if "deudor_a_pagar" in st.session_state and st.session_state["deudor_a_pagar"] in nombres_activos:
                index_defecto = nombres_activos.index(st.session_state["deudor_a_pagar"])
                
            cliente_seleccionado = st.selectbox("Selecciona la persona que va a pagar:", options=nombres_activos, index=index_defecto)
            
            fila_cliente = df_activos[df_activos["nombre"] == cliente_seleccionado].iloc[0]
            saldo_pendiente = float(fila_cliente["saldo"])
            
            st.info(f"Deuda actual de **{cliente_seleccionado}**: **${saldo_pendiente:,.2f}**")
            
            monto_pago = st.number_input(
                "Monto que entrega la persona ($):", 
                min_value=0.0, 
                max_value=saldo_pendiente,
                value=saldo_pendiente, 
                step=5.0, 
                format="%.2f",
                help="Por defecto viene el total para liquidar la cuenta completa."
            )
            
            fecha_pago = st.date_input("Fecha del pago:", value=date.today(), key="fecha_pago")
            
            if st.button("✅ Confirmar Pago", type="primary"):
                if monto_pago <= 0:
                    st.error("⚠️ El monto a pagar debe ser mayor a $0.")
                else:
                    with st.spinner("Actualizando en Google Sheets..."):
                        payload = {
                            "action": "payFiado",
                            "nombre": cliente_seleccionado,
                            "monto": float(monto_pago),
                            "fecha": fecha_pago.strftime("%Y-%m-%d")
                        }
                        if api_post(payload):
                            if monto_pago >= saldo_pendiente:
                                st.balloons()
                                st.success(f"🎉 ¡Cuenta liquidada por completo! **{cliente_seleccionado}** ya no aparece en la lista de deudores.")
                            else:
                                st.success(f"✅ ¡Abono registrado! Saldo restante: **${(saldo_pendiente - monto_pago):,.2f}**.")
                            
                            if "deudor_a_pagar" in st.session_state:
                                del st.session_state["deudor_a_pagar"]
                            st.rerun()

    # Acordeón con historial de movimientos de fiado
    with st.expander("📜 Ver historial reciente de fiados y pagos"):
        if df_hist_fiado_raw.empty:
            st.caption("Aún no hay historial de fiados registrado.")
        else:
            cols_show = [c for c in ["fecha", "nombre", "tipo", "monto", "notas"] if c in df_hist_fiado_raw.columns]
            st.dataframe(df_hist_fiado_raw[cols_show].tail(25).iloc[::-1], hide_index=True, use_container_width=True)

# ==========================================
# PESTAÑA 4: MÉTRICAS Y RESUMEN DEL DÍA
# ==========================================
with tab_metricas:
    col_t, col_f = st.columns([2, 1])
    with col_t:
        st.markdown("#### 📈 Resumen del Día")
    with col_f:
        fecha_seleccionada = st.date_input("Fecha:", value=date.today(), label_visibility="collapsed")
    
    fecha_str = fecha_seleccionada.strftime("%Y-%m-%d")
    
    if not df_movimientos_raw.empty:
        df_dia = df_movimientos_raw[df_movimientos_raw["fecha"] == fecha_str]
    else:
        df_dia = pd.DataFrame()
    
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
        st.metric(label="💵 Total Vendido", value=f"${total_ventas:,.2f}")
    with m2:
        st.metric(label="🛒 Total Comprado", value=f"${total_compras:,.2f}")
    
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
# PESTAÑA 5: HISTORIAL Y GESTIÓN
# ==========================================
with tab_historial:
    st.markdown("#### 📋 Movimientos de Hoy")
    fecha_hoy_str = date.today().strftime("%Y-%m-%d")
    
    if not df_movimientos_raw.empty:
        df_hoy = df_movimientos_raw[df_movimientos_raw["fecha"] == fecha_hoy_str]
    else:
        df_hoy = pd.DataFrame()
    
    if df_hoy.empty:
        st.caption("Aún no has registrado movimientos hoy.")
    else:
        st.write(f"Total registros hoy: **{len(df_hoy)}**")
        for _, row in df_hoy.iloc[::-1].iterrows():
            icono = "💵" if row["tipo"] == "Venta" else "🛒"
            color = "#16a34a" if row["tipo"] == "Venta" else "#dc2626"
            row_idx = row.get("_row_idx")
            
            with st.container():
                col_info, col_del = st.columns([5, 1])
                with col_info:
                    st.markdown(
                        f"**{icono} {row['tipo']} - {row['categoria']}**  \n"
                        f"Cantidad: `{row['cantidad']} pza` | Monto: <span style='color:{color}; font-weight:700;'>${row['monto']:,.2f}</span>",
                        unsafe_allow_html=True
                    )
                with col_del:
                    if row_idx is not None and st.button("🗑️", key=f"del_{row_idx}", help="Eliminar este registro de Google Sheets"):
                        with st.spinner("Eliminando..."):
                            api_post({"action": "deleteMovimiento", "row_idx": int(row_idx)})
                            st.toast("Movimiento eliminado en Google Sheets")
                            st.rerun()
                st.markdown("<hr style='margin: 4px 0 10px 0; border: none; border-top: 1px dashed #e2e8f0;'>", unsafe_allow_html=True)
