#### IMPORTAR MÓDULOS ####
import sqlite3
import datetime
from datetime import timezone
import os
import re

#### DEFINICIÓN DE COLORES ####
MAGENTA = "\033[35m"
RED = "\033[31m"
GREEN = "\033[32m"
RESET = "\033[0m"

#### CONSTANTES ####
DB_NAME = 'hamradio_logbook.db'

#### FUNCIONES DE INICIO ####
def iniciar_aplicacion():
    """Punto de entrada principal de la aplicación"""
    crear_base()
    mostrar_menu_principal()

#### FUNCIONES DEL MENÚ ####
def mostrar_menu_principal():
    """Muestra el menú principal y maneja las opciones"""
    opcion = 0
    while opcion != 7:
        imprimir_menu()
        
        try:
            opcion = int(input("\nSelecciona una opción: "))
        except ValueError:
            opcion = 0

        manejar_opcion(opcion)

    print("\n¡Hasta luego! 73")

def imprimir_menu():
    """Muestra las opciones del menú"""
    print(f"\n{GREEN}{'*' * 40}")
    print("Epelbyte HamRadio Logbook")
    print("version 1.0")
    print(f"{'*' * 40}{RESET}")
    print(f"{MAGENTA}1. Agregar contacto")
    print("2. Listar contactos")
    print("3. Importar desde ADIF")
    print("4. Exportar todo hacia ADIF")
    print("5. Exportar entradas de hoy a ADIF")  # Nueva opción
    print("6. Configurar estación")
    print(f"7. Salir{RESET}")

def manejar_opcion(opcion):
    """Dirige a la función correspondiente según la opción seleccionada"""
    acciones = {
        1: agregar_entrada,
        2: listar_entradas,
        3: importar_adif,
        4: exportar_adif,
        5: exportar_hoy_adif,
        6: configurar_estacion
        # La opción 7 es para salir y no necesita acción
    }
    
    if opcion in acciones:
        acciones[opcion]()
    elif opcion != 7:  # Solo muestra error si no es 7 (salir)
        print("\nOpción incorrecta, por favor intente nuevamente\n")

#### FUNCIONES DE BASE DE DATOS ####
def crear_base():
    """Crea la base de datos y tablas si no existen"""
    with conexion_db() as conn:
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS logbook (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                my_call TEXT NOT NULL,
                contact_call TEXT NOT NULL,
                frequency REAL, 
                band TEXT NOT NULL,
                mode TEXT NOT NULL,
                timestamp DATETIME NOT NULL,
                rst_sent TEXT,
                rst_received TEXT,
                comment TEXT,
                qth TEXT,
                name TEXT,
                power REAL,
                grid_locator TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS station_config (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                my_call TEXT,
                power TEXT,
                location TEXT,
                grid_locator TEXT,
                antenna TEXT,
                equipment TEXT,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')

def conexion_db():
    """Crea y retorna una conexión a la base de datos"""
    return sqlite3.connect(DB_NAME)

#### FUNCIONES DE CONFIGURACIÓN ####
def cargar_configuracion():
    """Carga la configuración de la estación desde la base de datos"""
    with conexion_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM station_config ORDER BY id DESC LIMIT 1')
        config = cursor.fetchone()
    
    return {
        'my_call': config[1] if config else '',
        'power': config[2] if config else '',
        'location': config[3] if config else '',
        'grid_locator': config[4] if config else '',
        'antenna': config[5] if config else '',
        'equipment': config[6] if config else ''
    } if config else {
        'my_call': '',
        'power': '',
        'location': '',
        'grid_locator': '',
        'antenna': '',
        'equipment': ''
    }

def guardar_configuracion(config):
    """Guarda la configuración de la estación en la base de datos"""
    with conexion_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO station_config 
            (my_call, power, location, grid_locator, antenna, equipment)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            config['my_call'],
            config['power'],
            config['location'],
            config['grid_locator'],
            config['antenna'],
            config['equipment']
        ))

#### FUNCIONES DEL LOGBOOK ####
def agregar_entrada():
    """Añade una nueva entrada al logbook"""
    config = cargar_configuracion()
    
    if not config['my_call']:
        print("\nAdvertencia: Configura tu estación primero (Opción 5).")
        return
    
    print("\n--- Añadir nueva entrada ---")
    
    datos = obtener_datos_entrada(config)
    
    with conexion_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO logbook 
            (my_call, contact_call, frequency, band, mode, timestamp, 
             rst_sent, rst_received, comment, qth, name, power, grid_locator)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            config['my_call'],
            datos['contact_call'],
            datos['frequency'],
            datos['band'],
            datos['mode'],
            datos['timestamp'],
            datos['rst_sent'],
            datos['rst_received'],
            datos['comment'],
            datos['qth'],
            datos['name'],
            datos['power'],
            datos['contact_grid']
        ))
    
    print("\n¡Entrada añadida correctamente!")

def obtener_datos_entrada(config):
    """Recopila los datos para una nueva entrada"""
    datos = {
        'contact_call': input("Indicativo del contacto: ").strip().upper(),
        'frequency': obtener_frecuencia_valida(),
        'band': determinar_banda(0),  # Se actualiza después
        'mode': input("Modo (SSB, CW, FT8, etc.): ").strip().upper(),
        'timestamp': obtener_timestamp(),
        'rst_sent': input("RST enviado (opcional): ").strip(),
        'rst_received': input("RST recibido (opcional): ").strip(),
        'name': input("Nombre (opcional): ").strip(),
        'qth': input("QTH (opcional): ").strip(),
        'contact_grid': input("Grid Locator del contacto (opcional): ").strip().upper(),
        'comment': input("Comentario (opcional, dejar en blanco para texto automático): ").strip(),
        'power': None
    }
    
    # Calcular banda basada en la frecuencia
    datos['band'] = determinar_banda(datos['frequency'])
    print(f"Banda calculada: {datos['band']}")
    
    # Comentario automático si no se especifica
    if not datos['comment'] and datos['name']:
        datos['comment'] = f"Muchas gracias {datos['name']} por tu contacto, 73!"
    
    # Manejo de potencia
    power_input = input(f"Potencia (W) [Config: {config['power']}]: ").strip()
    if power_input:
        try:
            datos['power'] = float(power_input)
        except ValueError:
            print("Potencia no válida, se usará la de configuración.")
    elif config['power']:
        try:
            datos['power'] = float(config['power'])
        except ValueError:
            pass
    
    return datos

def listar_entradas():
    """Lista todas las entradas del logbook"""
    config = cargar_configuracion()
    print(f"{GREEN}Libro de guardia de: {config.get('my_call', '')} {RESET}")
    print(f"{MAGENTA}{'ID':<8} {'Fecha y Hora':<16} {'Estación':<20} {'Banda y modo':<20} {'Comentario':<40}{RESET}")
    
    with conexion_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, timestamp, my_call, contact_call, frequency, band, mode, comment
            FROM logbook 
            ORDER BY timestamp DESC
        ''')
        entries = cursor.fetchall()
    
    if not entries:
        print("No hay entradas en el logbook.")
        return
    
    for entry in entries:
        print(f"{entry[0]}. {entry[1]:<15} | {entry[3]:<10} | {entry[4]} MHz ({entry[5]}) {entry[6]:<10} | {entry[7]}")
    
    entry_id = input("\nIntroduce el ID para ver detalles (o Enter para continuar): ").strip()
    if entry_id:
        try:
            mostrar_detalles_entrada(int(entry_id))
        except ValueError:
            print("ID no válido.")

def mostrar_detalles_entrada(entry_id):
    """Muestra los detalles completos de una entrada"""
    with conexion_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM logbook WHERE id = ?', (entry_id,))
        entry = cursor.fetchone()
    
    if not entry:
        print("Entrada no encontrada.")
        return
    
    print("\n--- Detalles de la entrada ---")
    detalles = [
        ("Indicativo", entry[2]),
        ("Contacto", entry[3]),
        ("Frecuencia", f"{entry[4]} MHz"),
        ("Banda", entry[5]),
        ("Modo", entry[6]),
        ("Fecha/Hora", entry[7]),
        ("RST enviado", entry[8]),
        ("RST recibido", entry[9]),
        ("Comentario", entry[10]),
        ("QTH", entry[11]),
        ("Nombre", entry[12]),
        ("Potencia", f"{entry[13]} W" if entry[13] else None),
        ("Grid Locator", entry[14])
    ]
    
    for nombre, valor in detalles:
        if valor:
            print(f"{nombre}: {valor}")

#### FUNCIONES ADIF ####
def exportar_adif():
    """Exporta el logbook a un archivo ADIF"""
    print("\n--- Exportar a ADIF ---")
    filename = input("Nombre del archivo (sin extensión): ").strip() or "hamradio_logbook"
    filename += ".adi"
    
    with conexion_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM logbook')
        entries = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write("HamRadio Logbook Export\n")
        f.write("<ADIF_VER:5>3.1.0\n")
        f.write("<PROGRAMID:11>HamLogbook\n")
        f.write(f"<CREATED_TIMESTAMP:15>{datetime.datetime.now(timezone.utc).strftime('%Y%m%d %H%M%S')}\n")
        f.write("<EOH>\n\n")
        
        for entry in entries:
            for col, val in zip(columns, entry):
                if col == 'id' or val is None or val == '':
                    continue
                
                tag = mapear_tag_adif(col)
                if not tag:
                    continue
                
                if col == 'timestamp':
                    dt = datetime.datetime.strptime(val, '%Y-%m-%d %H:%M:%S')
                    f.write(f"<{tag}:8>{dt.strftime('%Y%m%d')} <TIME_ON:6>{dt.strftime('%H%M%S')} ")
                elif col == 'frequency':
                    f.write(f"<{tag}:8>{val:.6f} ")
                else:
                    val_str = str(val)
                    f.write(f"<{tag}:{len(val_str)}>{val_str} ")
            
            f.write("<EOR>\n")
    
    print(f"\nLogbook exportado correctamente a {filename}")

def exportar_hoy_adif():
    """Exporta todas las entradas creadas hoy a un archivo ADIF"""
    hoy = datetime.datetime.now().strftime('%Y-%m-%d')
    nombre_archivo = f"logbook_{hoy}.adi"
    
    print(f"\n--- Exportando entradas de hoy ({hoy}) a {nombre_archivo} ---")
    
    with conexion_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM logbook 
            WHERE date(created_at) = date('now')
            ORDER BY created_at DESC
        ''')
        entries = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
    
    if not entries:
        print("No hay entradas creadas hoy para exportar.")
        return
    
    with open(nombre_archivo, 'w', encoding='utf-8') as f:
        # Cabecera ADIF
        f.write(f"HamRadio Logbook Export - Entradas del {hoy}\n")
        f.write("<ADIF_VER:5>3.1.0\n")
        f.write("<PROGRAMID:11>HamLogbook\n")
        f.write(f"<CREATED_TIMESTAMP:15>{datetime.datetime.now(timezone.utc).strftime('%Y%m%d %H%M%S')}\n")
        f.write("<EOH>\n\n")
        
        for entry in entries:
            for col, val in zip(columns, entry):
                if col == 'id' or val is None or val == '':
                    continue
                
                tag = mapear_tag_adif(col)
                if not tag:
                    continue
                
                if col == 'timestamp':
                    dt = datetime.datetime.strptime(val, '%Y-%m-%d %H:%M:%S')
                    f.write(f"<{tag}:8>{dt.strftime('%Y%m%d')} <TIME_ON:6>{dt.strftime('%H%M%S')} ")
                elif col == 'frequency':
                    f.write(f"<{tag}:8>{val:.6f} ")
                else:
                    val_str = str(val)
                    f.write(f"<{tag}:{len(val_str)}>{val_str} ")
            
            f.write("<EOR>\n")
    
    print(f"Se exportaron {len(entries)} entradas creadas hoy.")
    print(f"Archivo generado: {nombre_archivo}")    

def mapear_tag_adif(col):
    """Mapea nombres de columnas a tags ADIF"""
    tag_map = {
        'my_call': 'OPERATOR',
        'contact_call': 'CALL',
        'frequency': 'FREQ',
        'band': 'BAND',
        'mode': 'MODE',
        'timestamp': 'QSO_DATE',
        'rst_sent': 'RST_SENT',
        'rst_received': 'RST_RCVD',
        'comment': 'COMMENT',
        'qth': 'QTH',
        'name': 'NAME',
        'power': 'TX_PWR',
        'grid_locator': 'GRIDSQUARE'
    }
    return tag_map.get(col)

def importar_adif():
    """Importa entradas desde un archivo ADIF"""
    print("\n--- Importar desde ADIF ---")
    filename = input("Nombre del archivo ADIF (con extensión): ").strip()
    
    if not os.path.exists(filename):
        print("[ERROR] El archivo no existe.")
        return
        
    print(f"\nProcesando archivo: {filename}")
    
    try:
        with open(filename, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        content = preprocesar_adif(content)
        registros = procesar_contenido_adif(content)
        
        if registros['entries']:
            importar_registros_adif(registros)
        else:
            print("\nNo se encontraron registros válidos para importar")
            
    except Exception as e:
        print(f"\n[ERROR] Falla en la importación: {str(e)}")

#### FUNCIONES AUXILIARES ####
def determinar_banda(frecuencia):
    """Determina la banda basada en la frecuencia en MHz"""
    band_plan = {
        '160m': (1.8, 2.0),
        '80m': (3.5, 3.8),    
        '60m': (5.3515, 5.3665),
        '40m': (7.0, 7.3),
        '30m': (10.1, 10.15),
        '20m': (14.0, 14.35),  
        '17m': (18.068, 18.168),
        '15m': (21.0, 21.45),  
        '12m': (24.89, 24.99),
        '10m': (28.0, 29.7),   
        '6m': (50.0, 54.0),
        '2m': (144.0, 148.0),
        '1,2m': (220.0, 225.0),
        '70cm': (430.0, 440.0), 
        '23cm': (1240.0, 1300.0),
        '13cm': (2390.0, 2450.0),
        '9cm': (3300.0, 3400.0),
        '5cm': (5650.0, 5850.0),
        '3cm': (10000.0, 10500.0),
        '1,2cm': (24000.0, 24250.0),
        '6mm': (47000.0, 47200.0),
    }
    for banda, (low, high) in band_plan.items():
        if low <= frecuencia <= high:
            return banda
    return f"{frecuencia:.3f}MHz"

def obtener_timestamp():
    """Obtiene la fecha y hora del contacto"""
    while True:
        time_input = input("Fecha y hora (UTC, YYYY-MM-DD HH:MM o vacío para ahora): ").strip()
        
        if not time_input:
            return datetime.datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
        
        try:
            dt = datetime.datetime.strptime(time_input, '%Y-%m-%d %H:%M:%S')
            return dt.strftime('%Y-%m-%d %H:%M:%S')
        except ValueError:
            try:
                dt = datetime.datetime.strptime(time_input, '%Y-%m-%d %H:%M')
                return dt.strftime('%Y-%m-%d %H:%M:%S')
            except ValueError:
                print("Formato inválido. Usa YYYY-MM-DD HH:MM o deja vacío para hora actual.")

def obtener_frecuencia_valida():
    """Solicita una frecuencia válida al usuario"""
    while True:
        try:
            frequency = float(input("Frecuencia (MHz): ").strip())
            return frequency
        except ValueError:
            print("Por favor, introduce un número válido.")

def preprocesar_adif(content):
    """Preprocesa el contenido ADIF para estandarizarlo"""
    return content.replace('<QSO_DATE:8:D>', '<QSO_DATE:8>').replace('<TIME_ON:6:T>', '<TIME_ON:6>')

def procesar_contenido_adif(content):
    """Procesa el contenido ADIF y extrae los registros"""
    eoh_pos = content.upper().find('<EOH>')
    if eoh_pos >= 0:
        content = content[eoh_pos + 5:]
    
    registros = {
        'entries': [],
        'record_count': 0,
        'imported_count': 0,
        'skipped_count': 0
    }
    
    while '<EOR>' in content.upper():
        registros['record_count'] += 1
        eor_pos = content.upper().find('<EOR>')
        record = content[:eor_pos].strip()
        content = content[eor_pos + 5:]
        
        fields = extraer_campos_adif(record)
        if not validar_campos_obligatorios(fields, registros['record_count']):
            registros['skipped_count'] += 1
            continue
        
        registro = procesar_registro_adif(fields, registros['record_count'])
        if registro:
            registros['entries'].append(registro)
        else:
            registros['skipped_count'] += 1
    
    return registros

def extraer_campos_adif(record):
    """Extrae los campos de un registro ADIF"""
    fields = {}
    pos = 0
    
    while pos < len(record):
        if record[pos] != '<':
            pos += 1
            continue
            
        end_tag = record.find('>', pos)
        if end_tag == -1:
            break
            
        tag_info = record[pos + 1:end_tag]
        colon_pos = tag_info.find(':')
        
        if colon_pos == -1:
            tag = tag_info.upper()
            length = None
        else:
            tag = tag_info[:colon_pos].upper()
            try:
                length = int(tag_info[colon_pos + 1:])
            except ValueError:
                length = None
        
        pos = end_tag + 1
        
        if length is not None and length > 0:
            value = record[pos:pos + length]
            pos += length
        else:
            next_tag = record.find('<', pos)
            if next_tag == -1:
                value = record[pos:]
                pos = len(record)
            else:
                value = record[pos:next_tag]
                pos = next_tag
        
        fields[tag] = value.strip()
    
    return fields

def validar_campos_obligatorios(fields, record_count):
    """Valida que el registro ADIF tenga los campos obligatorios"""
    REQUIRED_FIELDS = ['CALL', 'BAND', 'MODE', 'QSO_DATE', 'TIME_ON']
    missing_required = [req_tag for req_tag in REQUIRED_FIELDS if req_tag not in fields]
    
    if missing_required:
        print(f"[WARN] Registro #{record_count} incompleto. Faltan: {missing_required}")
        return False
    return True

def procesar_registro_adif(fields, record_count):
    """Procesa un registro ADIF individual"""
    try:
        timestamp = generar_timestamp_adif(fields['QSO_DATE'], fields['TIME_ON'])
    except ValueError as e:
        print(f"[WARN] Registro #{record_count} - Error en fecha/hora: {e}")
        return None
    
    config = cargar_configuracion()
    contact_call = fields['CALL'].upper()
    
    if registro_existente(contact_call, timestamp):
        print(f"[INFO] Registro #{record_count} ya existe: {contact_call} a las {timestamp[:19]}")
        return None
    
    return {
        'my_call': config['my_call'],
        'contact_call': contact_call,
        'band': fields['BAND'].lower(),
        'mode': fields['MODE'].upper(),
        'timestamp': timestamp,
        'frequency': float(fields['FREQ']) if 'FREQ' in fields else None,
        'rst_sent': fields.get('RST_SENT'),
        'rst_received': fields.get('RST_RCVD'),
        'comment': fields.get('COMMENT') or fields.get('QSLMSG') or fields.get('QSLMSG_INTL'),
        'qth': fields.get('QTH'),
        'name': fields.get('NAME'),
        'grid_locator': fields.get('GRIDSQUARE', '').upper()[:6],
        'power': float(fields['TX_PWR']) if 'TX_PWR' in fields else None
    }

def generar_timestamp_adif(qso_date, time_on):
    """Genera un timestamp a partir de los campos ADIF"""
    time_on_padded = time_on.ljust(6, '0')[:6]
    dt = datetime.datetime.strptime(f"{qso_date}{time_on_padded}", '%Y%m%d%H%M%S')
    return dt.strftime('%Y-%m-%d %H:%M:%S')

def registro_existente(contact_call, timestamp):
    """Verifica si un registro ya existe en la base de datos"""
    with conexion_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT COUNT(*) FROM logbook 
            WHERE contact_call = ? AND timestamp = ?
        ''', (contact_call, timestamp[:19]))
        return cursor.fetchone()[0] > 0

def importar_registros_adif(registros):
    """Importa los registros ADIF a la base de datos"""
    with conexion_db() as conn:
        cursor = conn.cursor()
        
        for entry in registros['entries']:
            try:
                cursor.execute('''
                    INSERT INTO logbook 
                    (my_call, contact_call, frequency, band, mode, timestamp, 
                    rst_sent, rst_received, comment, qth, name, grid_locator, power)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    entry['my_call'],
                    entry['contact_call'],
                    entry.get('frequency'),
                    entry['band'],
                    entry['mode'],
                    entry['timestamp'],
                    entry.get('rst_sent'),
                    entry.get('rst_received'),
                    entry.get('comment'),
                    entry.get('qth'),
                    entry.get('name'),
                    entry.get('grid_locator'),
                    entry.get('power')
                ))
                registros['imported_count'] += 1
            except sqlite3.Error as e:
                print(f"[ERROR] SQLite: {str(e)}")
                continue
        
        conn.commit()
    
    print(f"\nResultados de importación:")
    print(f"- Total registros en archivo: {registros['record_count']}")
    print(f"- Registros nuevos importados: {registros['imported_count']}")
    print(f"- Registros duplicados omitidos: {registros['skipped_count']}")
    print(f"- Registros con errores: {registros['record_count'] - registros['imported_count'] - registros['skipped_count']}")

#### FUNCIONES DE CONFIGURACIÓN DE ESTACIÓN ####
def configurar_estacion():
    """Configura los datos de la estación"""
    config = cargar_configuracion()
    print("\n--- Configuración de la Estación ---")
    
    print("\nDatos actuales:")
    for key, value in config.items():
        print(f"{key.replace('_', ' ').title()}: {value}")
        
    print("\nIntroduce los nuevos valores (deja en blanco para mantener el actual):")
    
    config['my_call'] = input(f"Tu indicativo [{config['my_call']}]: ").strip().upper() or config['my_call']
    config['power'] = input(f"Potencia típica (W) [{config['power']}]: ").strip() or config['power']
    config['location'] = input(f"Ubicación (QTH) [{config['location']}]: ").strip() or config['location']
    config['grid_locator'] = obtener_grid_locator_valido(config['grid_locator'])
    config['antenna'] = input(f"Antena [{config['antenna']}]: ").strip() or config['antenna']
    config['equipment'] = input(f"Equipo [{config['equipment']}]: ").strip() or config['equipment']
    
    guardar_configuracion(config)
    print("\n¡Configuración guardada correctamente!")

def obtener_grid_locator_valido(valor_actual):
    """Solicita un grid locator válido al usuario"""
    while True:
        grid = input(f"Grid Locator (ej. GF15vc) [{valor_actual}]: ").strip().upper() or valor_actual
        if not grid or (len(grid) >= 4 and grid[0:2].isalpha() and grid[2:4].isdigit()):
            return grid
        print("Grid Locator debe tener al menos 4 caracteres (2 letras + 2 números)")