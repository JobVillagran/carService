# Car Service Citas Web

Proyecto académico para registrar citas de recepción de vehículos en un taller.

## Tecnologías

- Python 3
- Tkinter
- SQLite
- Programación orientada a objetos

No requiere paquetes externos de Python.

## Funcionalidades

- Consulta de vehículo por placa.
- Registro del contacto cuando la placa no existe.
- Tipo de placa y kilometraje.
- Servicios: Mantenimiento preventivo, Diagnóstico, Reparación y Mecánica general.
- Selección de agencia.
- Horarios de recepción de lunes a sábado, de 08:00 a 12:00, en intervalos de 30 minutos.
- Reparación reserva una hora continua sin traslapes.
- Capacidad de temporada baja y temporada alta.
- Asignación automática de jefe de taller.
- Guardado real de clientes, vehículos y citas en SQLite.
- Confirmación visual de la cita. El correo/SMS se simula para fines académicos.

## macOS

Se requiere Python 3 con Tkinter.

```bash
cd ~/Desktop/CarService
python3 car_service.py
```

Si `import tkinter` falla usando Homebrew, instala la variante de Tk correspondiente a tu versión de Python o usa el instalador oficial de Python para macOS.

También puedes ejecutar:

```bash
chmod +x run_mac.command
./run_mac.command
```

## Windows

Instala Python 3 desde python.org y asegúrate de incluir Tcl/Tk durante la instalación.

Desde PowerShell o CMD:

```powershell
cd $HOME\Desktop\CarService
python car_service.py
```

O ejecuta `run_windows.bat`.

## Base de datos

La primera ejecución crea automáticamente `car_service.db` en la misma carpeta que `car_service.py`.

Para consultar las citas:

```sql
SELECT * FROM CITA;
```

`car_service.db` está excluida de Git porque contiene datos locales de prueba.

## Alcance académico

El proyecto se limita al agendamiento de citas. No incluye facturación, inventario ni cobros.
