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

DB_PATH = "tienda.db"
CATEGORIAS = ["Refrescos", "Sabritas", "Galletas"]

# --- FUNCIONES DE BASE DE DATOS (SQLite) ---
def init_db():
    """Inicializa la base de datos y todas las tablas."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # Tabla de ventas y compras diarias
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
    # Tabla de deudores (saldos acumulados)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS deudores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT UNIQUE NOT NULL,
            saldo REAL NOT NULL DEFAULT 0.0,
            notas TEXT,
            fecha_actualizacion TEXT
        )
    """)
    # Historial de operaciones de fiado y pagos
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS movimientos_fiado (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            tipo TEXT NOT NULL,
            monto REAL NOT NULL,
            fecha TEXT NOT NULL,
            notas TEXT,
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

# --- FUNCIONES PARA DEUDORES Y FIADO ---
def registrar_fiado(nombre, monto, notas, fecha_str):
    """Registra una nueva deuda o suma al saldo acumulado del cliente."""
    nombre = nombre.strip().title()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Revisar si el cliente ya existe
    cursor.execute("SELECT id, saldo FROM deudores WHERE LOWER(nombre) = LOWER(?)", (nombre,))
    deudor = cursor.fetchone()
    
    if deudor:
        deudor_id, saldo_anterior = deudor
        nuevo_saldo = saldo_anterior + monto
        cursor.execute("""
            UPDATE deudores 
            SET saldo = ?, notas = ?, fecha_actualizacion = ?
            WHERE id = ?
        """, (nuevo_saldo, notas, fecha_str, deudor_id))
    else:
        cursor.execute("""
            INSERT INTO deudores (nombre, saldo, notas, fecha_actualizacion)
            VALUES (?, ?, ?, ?)
        """, (nombre, monto, notas, fecha_str))
    
    # Registrar en el historial de fiados
    cursor.execute("""
        INSERT INTO movimientos_fiado (nombre, tipo, monto, fecha, notas)
        VALUES (?, 'Fiado (+)', ?, ?, ?)
    """, (nombre, monto, fecha_str, notas))
    
    conn.commit()
    conn.close()

def registrar_pago_deudor(nombre, monto_pago, fecha_str):
    """Abona o liquida la deuda de una persona."""
    nombre = nombre.strip()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, saldo FROM deudores WHERE LOWER(nombre) = LOWER(?)", (nombre,))
    deudor = cursor.fetchone()
    
    if deudor:
        deudor_id, saldo_actual = deudor
        nuevo_saldo = max(0.0, saldo_actual - monto_pago)
        
        cursor.execute("""
            UPDATE deudores 
            SET saldo = ?, fecha_actualizacion = ?
            WHERE id = ?
        """, (nuevo_saldo, fecha_str, deudor_id))
        
        # Registrar en el historial
        cursor.execute("""
            INSERT INTO movimientos_fiado (nombre, tipo, monto, fecha, notas)
            VALUES (?, 'Pago/Liquidación (-)', ?, ?, ?)
        """, (nombre, monto_pago, fecha_str, f"Abono/Pago recibido: ${monto_pago:,.2f}"))
        
        conn.commit()
        conn.close()
        return nuevo_saldo, saldo_actual
    
    conn.close()
    return None, None

def obtener_deudores_activos():
    """Devuelve los clientes que tienen deuda pendiente mayor a cero."""
    conn = sqlite3.connect(DB_PATH)
    query = "SELECT id, nombre, saldo, notas, fecha_actualizacion FROM deudores WHERE saldo > 0 ORDER BY saldo DESC, nombre ASC"
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def obtener_todos_deudores():
    """Devuelve la lista de nombres registrados."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT nombre FROM deudores ORDER BY nombre ASC")
    nombres = [r[0] for r in cursor.fetchall()]
    conn.close()
    return nombres

def obtener_historial_fiado():
    """Devuelve los últimos movimientos de fiado y pagos."""
    conn = sqlite3.connect(DB_PATH)
    query = "SELECT fecha, nombre, tipo, monto, notas FROM movimientos_fiado ORDER BY id DESC LIMIT 20"
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

# Inicializar BD
init_db()

# --- CABECERA DE LA APP ---
col_head1, col_head2 = st.columns([4, 1])
with col_head1:
    st.markdown("### 🏪 Tienda de Abarrotes")
    st.caption(f"📅 Fecha actual: **{date.today().strftime('%d/%m/%Y')}**")

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
# PESTAÑA 3: DEUDORES / LO FIADO
# ==========================================
with tab_deudores:
    st.markdown("#### 📒 Control de Deudores y Fiado")
    
    # Subpestañas o acordeones para organizar celular
    accion_fiado = st.radio(
        "¿Qué deseas hacer?",
        ["👥 Ver Deudores Activos", "➕ Anotar Fiado", "💳 Registrar Pago"],
        horizontal=True,
        label_visibility="collapsed"
    )
    
    df_activos = obtener_deudores_activos()
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
                            📅 Última fecha: {row['fecha_actualizacion'] or 'Reciente'}
                            {f"<br>📝 Notas: {row['notas']}" if row['notas'] else ""}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Botón rápido para ir directo a pagar esta persona
                    if st.button(f"💵 Pagar cuenta de {row['nombre']}", key=f"btn_pay_{row['id']}"):
                        st.session_state["deudor_a_pagar"] = row["nombre"]
                        st.session_state["saldo_a_pagar"] = float(row["saldo"])
                        st.rerun()

    # --- SECCIÓN 2: ANOTAR NUEVO FIADO O ACUMULAR ---
    elif accion_fiado == "➕ Anotar Fiado":
        st.markdown("##### 📝 Anotar mercancía fiada")
        
        nombres_existentes = obtener_todos_deudores()
        usar_existente = False
        nombre_cliente = ""
        
        if nombres_existentes:
            modo_nombre = st.radio("Seleccionar cliente:", ["Escribir nuevo", "Elegir existente"], horizontal=True)
            if modo_nombre == "Elegir existente":
                nombre_cliente = st.selectbox("Cliente:", options=nombres_existentes)
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
                registrar_fiado(nombre_cliente, monto_fiado, notas_fiado, fecha_fiado.strftime("%Y-%m-%d"))
                st.success(f"¡Anotado con éxito! Se sumaron ${monto_fiado:,.2f} a la cuenta de {nombre_cliente.title()}.")
                st.rerun()

    # --- SECCIÓN 3: REGISTRAR PAGO / SALDAR CUENTA ---
    elif accion_fiado == "💳 Registrar Pago":
        st.markdown("##### 💵 Registrar Abono o Liquidación")
        
        if df_activos.empty:
            st.info("No hay clientes con saldo pendiente en este momento.")
        else:
            # Lista de deudores activos para cobrarles
            nombres_activos = df_activos["nombre"].tolist()
            
            # Si venía redirigido por el botón de pagar
            index_defecto = 0
            if "deudor_a_pagar" in st.session_state and st.session_state["deudor_a_pagar"] in nombres_activos:
                index_defecto = nombres_activos.index(st.session_state["deudor_a_pagar"])
                
            cliente_seleccionado = st.selectbox("Selecciona la persona que va a pagar:", options=nombres_activos, index=index_defecto)
            
            # Obtener saldo actual de la persona seleccionada
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
                    nuevo_saldo, _ = registrar_pago_deudor(cliente_seleccionado, monto_pago, fecha_pago.strftime("%Y-%m-%d"))
                    
                    if nuevo_saldo == 0.0:
                        st.balloons()
                        st.success(f"🎉 ¡Cuenta liquidada por completo! **{cliente_seleccionado}** ya pagó todo y **no volverá a aparecer en la lista de deudores**.")
                    else:
                        st.success(f"✅ ¡Abono registrado! **{cliente_seleccionado}** pagó ${monto_pago:,.2f}. Saldo restante: **${nuevo_saldo:,.2f}**.")
                    
                    # Limpiar estado si existía
                    if "deudor_a_pagar" in st.session_state:
                        del st.session_state["deudor_a_pagar"]
                    
                    st.rerun()

    # Acordeón con historial de movimientos de fiado
    with st.expander("📜 Ver historial reciente de fiados y pagos"):
        df_hist_fiado = obtener_historial_fiado()
        if df_hist_fiado.empty:
            st.caption("Aún no hay historial de fiados registrado.")
        else:
            st.dataframe(df_hist_fiado, hide_index=True, use_container_width=True)

# ==========================================
# PESTAÑA 4: MÉTRICAS Y RESUMEN DEL DÍA
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
# PESTAÑA 5: HISTORIAL Y GESTIÓN
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
