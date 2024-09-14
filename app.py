import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from fpdf import FPDF
from datetime import datetime
import base64

# Datos de la empresa
datos_empresa = {
    "cif": st.secrets["empresa"]["cif"],
    "nombre": st.secrets["empresa"]["nombre"], 
    "direccion": st.secrets["empresa"]["direccion"],
    "email": st.secrets["empresa"]["email"]
}

# Función para el inicio de sesión
def login():
    st.title("Login")
    username = st.text_input("Usuario")
    password = st.text_input("Contraseña", type="password")
    
    if st.button("Iniciar sesión"):
        if username == st.secrets["auth"]["username"] and password == st.secrets["auth"]["password"]:
            st.session_state['authenticated'] = True
            st.success("Has iniciado sesión exitosamente.")
        else:
            st.error("Usuario o contraseña incorrectos.")

# Función para cerrar sesión
def logout():
    if st.button("Cerrar sesión"):
        st.session_state['authenticated'] = False
        st.success("Has cerrado sesión exitosamente.")

# Función para generar el PDF (tu función existente)
def generar_pdf(datos_cliente, items_seleccionados, subtotal, iva, total, es_factura, numero_recibo, forma_pago, cambio=None):
    pdf = FPDF()
    pdf.add_page()
    
    # Agregar la fuente Unicode
    pdf.add_font('DejaVu', '', 'DejaVuSans.ttf', uni=True)
    pdf.add_font('DejaVu', 'B', 'DejaVuSans-Bold.ttf', uni=True)
    pdf.set_font('DejaVu', '', 12)
    
    # Agregar el logo centrado
    pdf.image('logo.png', x=80, y=10, w=50)
    pdf.ln(40)
    
    # Título
    pdf.set_font('DejaVu', 'B', 16)
    titulo = 'Factura' if es_factura else 'Recibo'
    pdf.cell(0, 10, titulo, ln=True, align='C')
    
    pdf.ln(10)
    
    # Información de la empresa
    pdf.set_font('DejaVu', '', 12)
    pdf.cell(0, 10, datos_empresa["nombre"], ln=True)
    pdf.cell(0, 10, f'CIF: {datos_empresa["cif"]}', ln=True)
    pdf.cell(0, 10, datos_empresa["direccion"], ln=True)
    pdf.ln(10)
    
    # Fecha y hora
    fecha_hora = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
    pdf.cell(0, 10, f'Fecha: {fecha_hora}', ln=True)
    
    # Datos del cliente si es factura
    if es_factura:
        pdf.ln(5)
        pdf.set_font('DejaVu', 'B', 12)
        pdf.cell(0, 10, 'Datos de Facturación:', ln=True)
        pdf.set_font('DejaVu', '', 12)
        pdf.cell(0, 10, f'Nombre o Razón Social: {datos_cliente["nombre"]}', ln=True)
        pdf.cell(0, 10, f'CIF/NIF: {datos_cliente["cif"]}', ln=True)
        pdf.cell(0, 10, f'Dirección: {datos_cliente["direccion"]}', ln=True)
        pdf.cell(0, 10, f'Email: {datos_cliente["email"]}', ln=True)
    else:
        pdf.ln(5)
        pdf.cell(0, 10, f'Cliente: {datos_cliente["nombre"]}', ln=True)
        pdf.cell(0, 10, f'Email: {datos_cliente["email"]}', ln=True)
    
    pdf.ln(10)
    
    # Tabla de productos
    pdf.set_font('DejaVu', 'B', 12)
    pdf.cell(60, 10, 'Producto', 1)
    pdf.cell(30, 10, 'Cantidad', 1, align='C')
    pdf.cell(40, 10, 'Precio Unitario', 1, align='R')
    pdf.cell(40, 10, 'Importe', 1, align='R')
    pdf.ln()
    
    pdf.set_font('DejaVu', '', 12)
    for item in items_seleccionados:
        pdf.cell(60, 10, item['Nombre'], 1)
        pdf.cell(30, 10, str(item['Cantidad']), 1, align='C')
        precio_unitario = float(item['Precio'].replace('€', '').replace(',', '.')) / 1.21
        subtotal_item = float(item['Subtotal'].replace('€', '').replace(',', '.')) / 1.21
        pdf.cell(40, 10, f"{precio_unitario:.2f}€", 1, align='R')
        pdf.cell(40, 10, f"{subtotal_item:.2f}€", 1, align='R')
        pdf.ln()
    
    # Subtotal, IVA y Total
    pdf.set_font('DejaVu', 'B', 12)
    pdf.cell(130, 10, 'Subtotal', 1)
    pdf.cell(40, 10, f"{subtotal:.2f}€", 1, align='R')
    pdf.ln()
    pdf.cell(130, 10, f'IVA (21%)', 1)
    pdf.cell(40, 10, f"{iva:.2f}€", 1, align='R')
    pdf.ln()
    pdf.cell(130, 10, 'Total', 1)
    pdf.cell(40, 10, f"{total:.2f}€", 1, align='R')
    pdf.ln(20)
    
    # Número de recibo
    pdf.set_font('DejaVu', '', 12)
    pdf.cell(0, 10, f'Número de {titulo}: V{numero_recibo}', ln=True)
    
    # Forma de pago
    pdf.cell(0, 10, f'Forma de pago: {forma_pago}', ln=True)
    if forma_pago.lower() == 'efectivo' and cambio is not None:
        pdf.cell(0, 10, f'Efectivo entregado: {cambio["efectivo_entregado"]:.2f}€', ln=True)
        pdf.cell(0, 10, f'Cambio: {cambio["cambio"]:.2f}€', ln=True)
    
    # Obtener contenido del PDF como bytes
    nombre_archivo = f'{titulo}_{numero_recibo}.pdf'
    return pdf, nombre_archivo

# Configuración de las credenciales y scopes
credentials_info = {
    "type": st.secrets["connections_gcs"]["type"],
    "project_id": st.secrets["connections_gcs"]["project_id"],
    "private_key_id": st.secrets["connections_gcs"]["private_key_id"],
    "private_key": st.secrets["connections_gcs"]["private_key"],
    "client_email": st.secrets["connections_gcs"]["client_email"],
    "client_id": st.secrets["connections_gcs"]["client_id"],
    "auth_uri": st.secrets["connections_gcs"]["auth_uri"],
    "token_uri": st.secrets["connections_gcs"]["token_uri"],
    "auth_provider_x509_cert_url": st.secrets["connections_gcs"]["auth_provider_x509_cert_url"],
    "client_x509_cert_url": st.secrets["connections_gcs"]["client_x509_cert_url"],
}

# Reemplazar '\\n' en la clave privada
credentials_info["private_key"] = credentials_info["private_key"].replace('\\n', '\n')

# Definir los scopes para Sheets y Drive
scopes = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive.metadata.readonly'
]

# Crear las credenciales
creds = Credentials.from_service_account_info(credentials_info, scopes=scopes)

# Autorizar cliente de gspread
client = gspread.authorize(creds)

# Construir el servicio de la API de Drive
drive_service = build('drive', 'v3', credentials=creds)

# Leer datos de Google Sheets
@st.cache_data
def cargar_datos():
    hoja_productos = client.open('Slowburn - Dashboard').worksheet('Productos')
    data_productos = hoja_productos.get_all_records()
    df_productos = pd.DataFrame(data_productos)
    # Preprocess the 'Precio' column
    df_productos['Precio'] = df_productos['Precio'].astype(str)  # Ensure the column is of type string
    df_productos['Precio'] = df_productos['Precio'].str.replace('€', '')  # Remove euro sign
    df_productos['Precio'] = df_productos['Precio'].str.replace(',', '.')  # Replace comma with dot
    df_productos['Precio'] = pd.to_numeric(df_productos['Precio'], errors='coerce')  # Convert to numeric
    
    # Filter products that are available
    df_productos = df_productos.loc[df_productos['Disponible'] == "Si"]
    return df_productos

def obtener_ultimo_id_venta():
    hoja_ventas = client.open('Slowburn - Dashboard').worksheet('Ventas')
    data_ventas = hoja_ventas.get_all_records()
    df_ventas = pd.DataFrame(data_ventas)

    # Obtener el último ID de Venta (asumiendo que los IDs están ordenados)
    ultimo_id_venta = df_ventas['ID de Venta'].iloc[-1]
    
    # Extraer el número de la venta (eliminando la 'V')
    ultimo_numero_venta = int(ultimo_id_venta[1:])  # Convierte 'VXXXXXXXXX' a 'XXXXXXXXX'
    
    # Incrementar el número de venta
    nuevo_numero_venta = ultimo_numero_venta + 1
    
    # Formatear el nuevo número de venta con el prefijo 'V'
    nuevo_id_venta = f'V{nuevo_numero_venta:09d}'
    
    return nuevo_id_venta

# Función para escribir una nueva fila en la hoja de ventas
def escribir_nueva_venta(fecha_venta, id_venta, id_producto, producto, cantidad, precio_con_iva, precio_sin_iva, id_cliente, nombre_cliente, apellidos_cliente, email_cliente):
    hoja_ventas = client.open('Slowburn - Dashboard').worksheet('Ventas')
    
    # Crear una nueva fila con los datos de la venta
    nueva_fila = [
        fecha_venta,
        id_venta,
        id_producto,
        producto,
        cantidad,
        f"€{precio_con_iva:.2f}",  # Formatear el precio con IVA
        f"{precio_con_iva:.2f}",
        f"€{precio_sin_iva:.2f}",  # Formatear el precio sin IVA
        f"{precio_sin_iva:.2f}",
        id_cliente,
        nombre_cliente,
        apellidos_cliente,
        email_cliente
    ]
    
    # Añadir la nueva fila a la hoja
    hoja_ventas.append_row(nueva_fila)

# Función principal para la app
def main():
    if 'authenticated' not in st.session_state:
        st.session_state['authenticated'] = False
    
    # Mostrar el login si no está autenticado
    if not st.session_state['authenticated']:
        login()
    else:
        logout()
        st.title('Generador de Recibos y Facturas - SlowBurn')
        
        df_productos = cargar_datos()
        if df_productos.empty:
            st.error('No hay productos disponibles.')
            return
        
        st.header('Selecciona los productos y cantidades')
        
        # Crear una lista para almacenar las cantidades
        cantidades = {}

        # Crear una lista para almacenar las cantidades en st.session_state
        if 'cantidades' not in st.session_state:
            st.session_state['cantidades'] = {}
        
        # Mostrar los productos y campos para ingresar cantidades
        for index, row in df_productos.iterrows():
            col1, col2, col3 = st.columns([2, 1, 1])
            with col1:
                st.write(row['Nombre'])
            with col2:
                st.write(f"{row['Precio']}€")
            with col3:
                cantidad = st.number_input(
                    label=f"Cantidad",
                    min_value=0,
                    value=0,
                    step=1,
                    key=f"cantidad_{index}"
                )
                st.session_state['cantidades'][row['Nombre']] = cantidad
        
        # Calcular el total
        total = 0
        items_seleccionados = []
        for index, row in df_productos.iterrows():
            nombre_producto = row['Nombre']
            precio = row['Precio']
            cantidad = st.session_state['cantidades'][nombre_producto]
            if cantidad > 0:
                subtotal = precio * cantidad
                items_seleccionados.append({
                    'Nombre': nombre_producto,
                    'Precio': f"{precio:.2f}€",
                    'Cantidad': cantidad,
                    'Subtotal': f"{subtotal:.2f}€"
                })
                total += subtotal
        
        st.write('---')
        st.write('**Resumen de la compra:**')
        
        if items_seleccionados:
            df_resumen = pd.DataFrame(items_seleccionados)
            st.table(df_resumen[['Nombre', 'Precio', 'Cantidad', 'Subtotal']])
            st.write(f"**Total:** {total:.2f}€")
        else:
            st.write('No se han seleccionado productos.')
        
        opcion_factura = st.checkbox('¿El cliente requiere factura?')
        
        if opcion_factura:
            st.subheader('Datos de facturación del cliente')
            nombre_cliente = st.text_input('Nombre o Razón Social')
            cif_cliente = st.text_input('CIF/NIF')
            direccion_cliente = st.text_input('Dirección')
        else:
            nombre_cliente = st.text_input('Nombre del cliente')
            apellidos_cliente = st.text_input('Apellidos del cliente')
        email_cliente = st.text_input('Email del cliente')
        
        # Forma de pago
        st.subheader('Forma de pago')
        forma_pago = st.selectbox('Seleccione la forma de pago', ['Efectivo', 'Tarjeta', 'Bizum'])
        efectivo_entregado = None
        cambio = None
        if forma_pago == 'Efectivo':
            efectivo_entregado = st.number_input('Efectivo entregado (€)', min_value=0.0, value=0.0, step=0.01)
            if efectivo_entregado < total:
                st.error('El efectivo entregado no puede ser menor que el total.')
                return
            cambio = efectivo_entregado - total
        
        if st.button('Generar PDF'):
            if not items_seleccionados:
                st.error('Debe seleccionar al menos un producto con cantidad mayor a cero.')
                return
            if not nombre_cliente or not email_cliente:
                st.error('Por favor, ingrese los datos del cliente.')
                return
            
            # Calcular subtotal y IVA
            subtotal = total / 1.21  # Si el IVA está incluido en el precio
            iva = total - subtotal
            
            # Obtener el nuevo número de recibo (ID de Venta incrementado)
            numero_recibo = obtener_ultimo_id_venta()
            
            # Obtener nuevo ID de cliente si no es facturación
            id_cliente = "CUSTOMER_FERIA"
            
            # Crear diccionario para el cambio si es efectivo
            cambio_dict = None
            if forma_pago == 'Efectivo':
                cambio_dict = {
                    'efectivo_entregado': efectivo_entregado,
                    'cambio': cambio
                }
            
            # Generar el PDF del recibo o factura
            datos_cliente = {
                'nombre': nombre_cliente,
                'cif': cif_cliente if opcion_factura else '',
                'direccion': direccion_cliente if opcion_factura else '',
                'email': email_cliente
            }
            pdf, nombre_archivo_pdf = generar_pdf(
                datos_cliente,
                items_seleccionados,
                subtotal,
                iva,
                total,
                opcion_factura,
                numero_recibo,
                forma_pago,
                cambio=cambio_dict
            )
            
            # Agregar la venta a la hoja de ventas
            fecha_venta = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
            for item in items_seleccionados:
                if not opcion_factura:
                    escribir_nueva_venta(
                        fecha_venta,
                        numero_recibo,
                        f"P{str(index).zfill(9)}",  # Simulación del ID de Producto
                        item['Nombre'],
                        item['Cantidad'],
                        float(item['Subtotal'].replace('€', '').replace(',', '.')),
                        subtotal,
                        id_cliente,
                        nombre_cliente,
                        apellidos_cliente,
                        email_cliente
                    )
                else:
                    escribir_nueva_venta(
                        fecha_venta,
                        numero_recibo,
                        f"P{str(index).zfill(9)}",  # Simulación del ID de Producto
                        item['Nombre'],
                        item['Cantidad'],
                        float(item['Subtotal'].replace('€', '').replace(',', '.')),
                        subtotal,
                        id_cliente,
                        "",
                        "",
                        ""
                    )
            
            # Resetear las órdenes
            def reset_orders():
                st.session_state['cantidades'] = {}
            reset_orders()
            
            st.success('PDF generado exitosamente y venta registrada.')
            
            def create_download_link(val, filename):
                b64 = base64.b64encode(val)  # val looks like b'...'
                return f'<a href="data:application/octet-stream;base64,{b64.decode()}" download="{filename}">Download file</a>'
            
            html = create_download_link(pdf.output(dest="S"), nombre_archivo_pdf)
            st.markdown(html, unsafe_allow_html=True)

if __name__ == '__main__':
    main()
