import sqlite3
import re
from pathlib import Path
from datetime import datetime, timedelta
import tkinter as tk
from tkinter import ttk, messagebox

APP_NAME = "Car Service Citas Web"
BASE_DIR = Path(__file__).resolve().parent
DB_NAME = BASE_DIR / "car_service.db"

BLUE = "#0B4F8A"
LIGHT = "#F3F4F6"
WHITE = "#FFFFFF"
TEXT = "#1F2937"


class Database:
    def __init__(self):
        self.conn = sqlite3.connect(str(DB_NAME))
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.create_schema()
        self.seed()

    def create_schema(self):
        self.conn.executescript("""
        CREATE TABLE IF NOT EXISTS CLIENTE(
            id_cliente INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            apellido TEXT NOT NULL,
            telefono TEXT NOT NULL,
            nit TEXT,
            correo TEXT,
            activo INTEGER NOT NULL DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS VEHICULO(
            id_vehiculo INTEGER PRIMARY KEY AUTOINCREMENT,
            id_cliente INTEGER NOT NULL,
            tipo_placa TEXT NOT NULL,
            numero_placa TEXT NOT NULL UNIQUE,
            kilometraje_actual INTEGER NOT NULL,
            activo INTEGER NOT NULL DEFAULT 1,
            FOREIGN KEY(id_cliente) REFERENCES CLIENTE(id_cliente)
        );
        CREATE TABLE IF NOT EXISTS AGENCIA(
            id_agencia INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            direccion TEXT,
            telefono TEXT,
            activa INTEGER NOT NULL DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS TIPO_SERVICIO(
            id_servicio INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            duracion_min INTEGER NOT NULL,
            requiere_hora_continua INTEGER NOT NULL DEFAULT 0,
            activo INTEGER NOT NULL DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS JEFE_TALLER(
            id_jefe INTEGER PRIMARY KEY AUTOINCREMENT,
            id_agencia INTEGER NOT NULL,
            nombre TEXT NOT NULL,
            activo INTEGER NOT NULL DEFAULT 1,
            FOREIGN KEY(id_agencia) REFERENCES AGENCIA(id_agencia)
        );
        CREATE TABLE IF NOT EXISTS TEMPORADA(
            id_temporada INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            fecha_inicio TEXT NOT NULL,
            fecha_fin TEXT NOT NULL,
            capacidad_por_intervalo INTEGER NOT NULL,
            activa INTEGER NOT NULL DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS CITA(
            id_cita INTEGER PRIMARY KEY AUTOINCREMENT,
            id_vehiculo INTEGER NOT NULL,
            id_agencia INTEGER NOT NULL,
            id_servicio INTEGER NOT NULL,
            id_jefe INTEGER NOT NULL,
            id_temporada INTEGER,
            fecha TEXT NOT NULL,
            hora_inicio TEXT NOT NULL,
            hora_fin TEXT NOT NULL,
            kilometraje INTEGER NOT NULL,
            estado TEXT NOT NULL DEFAULT 'Programada',
            FOREIGN KEY(id_vehiculo) REFERENCES VEHICULO(id_vehiculo),
            FOREIGN KEY(id_agencia) REFERENCES AGENCIA(id_agencia),
            FOREIGN KEY(id_servicio) REFERENCES TIPO_SERVICIO(id_servicio),
            FOREIGN KEY(id_jefe) REFERENCES JEFE_TALLER(id_jefe),
            FOREIGN KEY(id_temporada) REFERENCES TEMPORADA(id_temporada)
        );
        """)
        self.conn.commit()

    def seed(self):
        c = self.conn.cursor()
        if c.execute("SELECT COUNT(*) FROM AGENCIA").fetchone()[0] == 0:
            c.executemany(
                "INSERT INTO AGENCIA(nombre,direccion,telefono) VALUES(?,?,?)",
                [("Agencia Central","Dubai","04-555-0101"),
                 ("Agencia Norte","Dubai","04-555-0102")]
            )
        if c.execute("SELECT COUNT(*) FROM TIPO_SERVICIO").fetchone()[0] == 0:
            c.executemany(
                "INSERT INTO TIPO_SERVICIO(nombre,duracion_min,requiere_hora_continua) VALUES(?,?,?)",
                [("Mantenimiento preventivo",30,0),
                 ("Diagnóstico",30,0),
                 ("Reparación",60,1),
                 ("Mecánica general",30,0)]
            )
        if c.execute("SELECT COUNT(*) FROM JEFE_TALLER").fetchone()[0] == 0:
            agencies=c.execute("SELECT id_agencia,nombre FROM AGENCIA").fetchall()
            rows=[]
            for a in agencies:
                names=("Juan Pérez","Carlos López") if a["nombre"]=="Agencia Central" else ("Ana Torres","Sofía Ramírez")
                rows.extend((a["id_agencia"],n) for n in names)
            c.executemany("INSERT INTO JEFE_TALLER(id_agencia,nombre) VALUES(?,?)",rows)
        if c.execute("SELECT COUNT(*) FROM TEMPORADA").fetchone()[0] == 0:
            c.executemany(
                "INSERT INTO TEMPORADA(nombre,fecha_inicio,fecha_fin,capacidad_por_intervalo) VALUES(?,?,?,?)",
                [("Temporada baja 2026","2026-01-01","2026-12-31",1),
                 ("Temporada alta Semana Santa 2026","2026-03-29","2026-04-05",3),
                 ("Temporada alta Navidad 2026","2026-12-01","2026-12-31",3)]
            )
        self.conn.commit()

    def agencies(self):
        return self.conn.execute("SELECT * FROM AGENCIA WHERE activa=1 ORDER BY nombre").fetchall()

    def services(self):
        return self.conn.execute("SELECT * FROM TIPO_SERVICIO WHERE activo=1 ORDER BY id_servicio").fetchall()

    def vehicle(self, plate):
        return self.conn.execute("""
            SELECT v.*,c.nombre,c.apellido,c.telefono,c.nit,c.correo
            FROM VEHICULO v JOIN CLIENTE c ON c.id_cliente=v.id_cliente
            WHERE UPPER(v.numero_placa)=UPPER(?) AND v.activo=1
        """,(plate.strip(),)).fetchone()

    def season(self, date):
        return self.conn.execute("""
            SELECT * FROM TEMPORADA
            WHERE activa=1 AND DATE(?) BETWEEN DATE(fecha_inicio) AND DATE(fecha_fin)
            ORDER BY capacidad_por_intervalo DESC LIMIT 1
        """,(date,)).fetchone()

    def capacity(self, date):
        s=self.season(date)
        return s["capacidad_por_intervalo"] if s else 1

    def service(self, name):
        return self.conn.execute("SELECT * FROM TIPO_SERVICIO WHERE nombre=?",(name,)).fetchone()

    def overlap(self, date, start, end):
        return self.conn.execute("""
            SELECT COUNT(*) FROM CITA
            WHERE fecha=? AND estado='Programada'
              AND hora_inicio < ? AND hora_fin > ?
        """,(date,end,start)).fetchone()[0]

    def available(self, date, start, duration):
        st=datetime.strptime(f"{date} {start}","%Y-%m-%d %H:%M")
        en=st+timedelta(minutes=duration)
        close=datetime.strptime(f"{date} 12:00","%Y-%m-%d %H:%M")
        if en>close:
            return False
        if duration==60:
            return self.overlap(date,st.strftime("%H:%M"),en.strftime("%H:%M"))==0
        return self.overlap(date,st.strftime("%H:%M"),en.strftime("%H:%M")) < self.capacity(date)

    def slots(self, date, duration):
        cur=datetime.strptime(f"{date} 08:00","%Y-%m-%d %H:%M")
        end=datetime.strptime(f"{date} 12:00","%Y-%m-%d %H:%M")
        out=[]
        while cur<end:
            value=cur.strftime("%H:%M")
            if self.available(date,value,duration):
                out.append(value)
            cur+=timedelta(minutes=30)
        return out

    def chief(self, agency_id, date):
        return self.conn.execute("""
            SELECT j.id_jefe,j.nombre,COUNT(c.id_cita) total
            FROM JEFE_TALLER j
            LEFT JOIN CITA c ON c.id_jefe=j.id_jefe AND c.fecha=? AND c.estado='Programada'
            WHERE j.id_agencia=? AND j.activo=1
            GROUP BY j.id_jefe,j.nombre
            ORDER BY total,j.id_jefe LIMIT 1
        """,(date,agency_id)).fetchone()

    def save(self, d):
        cur=self.conn.cursor()
        cur.execute("BEGIN IMMEDIATE")
        try:
            v=self.vehicle(d["placa"])
            if v:
                vehicle_id=v["id_vehiculo"]
                cur.execute("UPDATE VEHICULO SET kilometraje_actual=?,tipo_placa=? WHERE id_vehiculo=?",
                            (d["km"],d["tipo"],vehicle_id))
            else:
                cur.execute("INSERT INTO CLIENTE(nombre,apellido,telefono,nit,correo) VALUES(?,?,?,?,?)",
                            (d["nombre"],d["apellido"],d["telefono"],d["nit"],d["correo"]))
                client_id=cur.lastrowid
                cur.execute("""INSERT INTO VEHICULO
                    (id_cliente,tipo_placa,numero_placa,kilometraje_actual)
                    VALUES(?,?,?,?)""",(client_id,d["tipo"],d["placa"],d["km"]))
                vehicle_id=cur.lastrowid

            service=self.service(d["servicio"])
            if not self.available(d["fecha"],d["hora"],service["duracion_min"]):
                raise ValueError("El horario ya no está disponible.")

            chief=self.chief(d["agencia_id"],d["fecha"])
            if not chief:
                raise ValueError("No hay jefe de taller disponible.")

            st=datetime.strptime(f'{d["fecha"]} {d["hora"]}',"%Y-%m-%d %H:%M")
            en=st+timedelta(minutes=service["duracion_min"])
            season=self.season(d["fecha"])
            cur.execute("""INSERT INTO CITA
                (id_vehiculo,id_agencia,id_servicio,id_jefe,id_temporada,
                 fecha,hora_inicio,hora_fin,kilometraje,estado)
                VALUES(?,?,?,?,?,?,?,?,?,'Programada')""",
                (vehicle_id,d["agencia_id"],service["id_servicio"],chief["id_jefe"],
                 season["id_temporada"] if season else None,d["fecha"],d["hora"],
                 en.strftime("%H:%M"),d["km"]))
            cid=cur.lastrowid
            self.conn.commit()
            return cid,chief["nombre"],en.strftime("%H:%M")
        except Exception:
            self.conn.rollback()
            raise

    def close(self):
        self.conn.close()


class CarServiceApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_NAME)
        self.geometry("1040x690")
        self.minsize(960,650)
        self.configure(bg=LIGHT)
        self.db=Database()
        self.vehicle_data=None
        self.agencies_data=self.db.agencies()
        self.services_data=self.db.services()
        self.agency_map={x["nombre"]:x["id_agencia"] for x in self.agencies_data}
        self.service_map={x["nombre"]:x for x in self.services_data}
        self.make_styles()
        self.build()
        self.date.set(datetime.now().strftime("%Y-%m-%d"))
        self.agency.set(self.agencies_data[0]["nombre"])
        self.service.set(self.services_data[0]["nombre"])
        self.refresh_slots()
        self.protocol("WM_DELETE_WINDOW",self.close_app)

    def make_styles(self):
        s=ttk.Style(self)
        s.theme_use("clam")
        s.configure("TLabel",background=WHITE,foreground=TEXT,font=("Arial",11))
        s.configure("Section.TLabel",background=WHITE,foreground=BLUE,font=("Arial",12,"bold"))
        s.configure("TButton",font=("Arial",11,"bold"),padding=7)
        s.configure("Blue.TButton",background=BLUE,foreground=WHITE)
        s.configure("TEntry",font=("Arial",11),padding=4)
        s.configure("TCombobox",font=("Arial",11),padding=4)

    def build(self):
        header=tk.Frame(self,bg=BLUE,height=72)
        header.pack(fill="x")
        header.pack_propagate(False)

        logo=tk.Canvas(header,width=55,height=44,bg=BLUE,highlightthickness=0)
        logo.pack(side="left",padx=(20,8),pady=14)
        logo.create_rectangle(10,15,44,29,outline=WHITE,width=2)
        logo.create_polygon(17,15,23,8,35,8,41,15,outline=WHITE,fill=BLUE,width=2)
        logo.create_oval(14,26,22,34,outline=WHITE,width=2)
        logo.create_oval(34,26,42,34,outline=WHITE,width=2)

        box=tk.Frame(header,bg=BLUE)
        box.pack(side="left",pady=10)
        tk.Label(box,text="CAR SERVICE",bg=BLUE,fg=WHITE,font=("Arial",19,"bold")).pack(anchor="w")
        tk.Label(box,text="Reserva tu cita de taller",bg=BLUE,fg=WHITE,font=("Arial",11)).pack(anchor="w")

        main=tk.Frame(self,bg=LIGHT)
        main.pack(fill="both",expand=True,padx=18,pady=16)
        left=tk.Frame(main,bg=WHITE,bd=1,relief="solid")
        right=tk.Frame(main,bg=WHITE,bd=1,relief="solid")
        left.pack(side="left",fill="both",expand=True,padx=(0,8))
        right.pack(side="left",fill="both",expand=True,padx=(8,0))
        self.build_left(left)
        self.build_right(right)

        foot=tk.Frame(self,bg=LIGHT)
        foot.pack(fill="x",padx=18,pady=(0,16))
        self.status=tk.StringVar(value="Complete los datos.")
        tk.Label(foot,textvariable=self.status,bg=LIGHT,fg=TEXT,font=("Arial",10)).pack(side="left")
        ttk.Button(foot,text="AGENDAR CITA",style="Blue.TButton",command=self.schedule).pack(side="right")

    def field(self,parent,label,var,row,col=0):
        ttk.Label(parent,text=label).grid(row=row,column=col,sticky="w",padx=12,pady=(6,2))
        e=ttk.Entry(parent,textvariable=var)
        e.grid(row=row+1,column=col,sticky="ew",padx=12,pady=(0,4))
        return e

    def build_left(self,p):
        p.columnconfigure(0,weight=1); p.columnconfigure(1,weight=1)
        ttk.Label(p,text="A. Vehículo",style="Section.TLabel").grid(row=0,column=0,columnspan=2,sticky="w",padx=12,pady=(12,4))

        self.tipo=tk.StringVar(value="Particular")
        self.placa=tk.StringVar()
        self.km=tk.StringVar()
        ttk.Label(p,text="Tipo de placa *").grid(row=1,column=0,sticky="w",padx=12,pady=(6,2))
        ttk.Combobox(p,textvariable=self.tipo,values=["Particular","Comercial","Motocicleta"],state="readonly").grid(row=2,column=0,sticky="ew",padx=12)

        ttk.Label(p,text="Número de placa *").grid(row=1,column=1,sticky="w",padx=12,pady=(6,2))
        platebox=tk.Frame(p,bg=WHITE); platebox.grid(row=2,column=1,sticky="ew",padx=12); platebox.columnconfigure(0,weight=1)
        pe=ttk.Entry(platebox,textvariable=self.placa); pe.grid(row=0,column=0,sticky="ew")
        ttk.Button(platebox,text="Buscar",command=self.search_plate).grid(row=0,column=1,padx=(5,0))

        self.field(p,"Kilometraje *",self.km,3,0).grid(columnspan=2)
        self.vstatus=tk.StringVar(value="Ingrese una placa.")
        tk.Label(p,textvariable=self.vstatus,bg=WHITE,fg=BLUE,font=("Arial",9,"italic")).grid(row=5,column=0,columnspan=2,sticky="w",padx=12,pady=6)

        ttk.Separator(p).grid(row=6,column=0,columnspan=2,sticky="ew",padx=12,pady=5)
        ttk.Label(p,text="B. Contacto (solo si la placa no existe)",style="Section.TLabel").grid(row=7,column=0,columnspan=2,sticky="w",padx=12,pady=(8,4))

        self.nombre=tk.StringVar(); self.apellido=tk.StringVar(); self.telefono=tk.StringVar()
        self.nit=tk.StringVar(); self.correo=tk.StringVar()
        e1=self.field(p,"Nombre *",self.nombre,8,0)
        e2=self.field(p,"Apellido *",self.apellido,8,1)
        e3=self.field(p,"Teléfono *",self.telefono,10,0)
        e4=self.field(p,"NIT *",self.nit,10,1)
        e5=self.field(p,"Correo electrónico *",self.correo,12,0); e5.grid(columnspan=2)
        self.contact_entries=[e1,e2,e3,e4,e5]

    def build_right(self,p):
        p.columnconfigure(0,weight=1); p.columnconfigure(1,weight=1)
        ttk.Label(p,text="C. Servicio",style="Section.TLabel").grid(row=0,column=0,columnspan=2,sticky="w",padx=12,pady=(12,4))

        self.service=tk.StringVar(); self.agency=tk.StringVar()
        ttk.Label(p,text="Tipo de servicio *").grid(row=1,column=0,sticky="w",padx=12,pady=(6,2))
        s=ttk.Combobox(p,textvariable=self.service,values=[x["nombre"] for x in self.services_data],state="readonly")
        s.grid(row=2,column=0,sticky="ew",padx=12); s.bind("<<ComboboxSelected>>",lambda e:self.refresh_slots())

        ttk.Label(p,text="Agencia *").grid(row=1,column=1,sticky="w",padx=12,pady=(6,2))
        a=ttk.Combobox(p,textvariable=self.agency,values=[x["nombre"] for x in self.agencies_data],state="readonly")
        a.grid(row=2,column=1,sticky="ew",padx=12); a.bind("<<ComboboxSelected>>",lambda e:self.update_chief())

        ttk.Separator(p).grid(row=3,column=0,columnspan=2,sticky="ew",padx=12,pady=10)
        ttk.Label(p,text="D. Fecha y horario",style="Section.TLabel").grid(row=4,column=0,columnspan=2,sticky="w",padx=12,pady=(2,4))

        self.date=tk.StringVar(); self.time=tk.StringVar()
        de=self.field(p,"Fecha * (YYYY-MM-DD)",self.date,5,0)
        de.bind("<FocusOut>",lambda e:self.refresh_slots())

        ttk.Label(p,text="Horario disponible *").grid(row=5,column=1,sticky="w",padx=12,pady=(6,2))
        self.time_combo=ttk.Combobox(p,textvariable=self.time,state="readonly")
        self.time_combo.grid(row=6,column=1,sticky="ew",padx=12)
        ttk.Button(p,text="Actualizar horarios",command=self.refresh_slots).grid(row=7,column=0,columnspan=2,pady=8)

        ttk.Label(p,text="Jefe de taller").grid(row=8,column=0,columnspan=2,sticky="w",padx=12,pady=(6,2))
        self.chief_var=tk.StringVar(value="Asignación automática")
        ttk.Entry(p,textvariable=self.chief_var,state="readonly").grid(row=9,column=0,columnspan=2,sticky="ew",padx=12)

        self.season_var=tk.StringVar()
        tk.Label(p,textvariable=self.season_var,bg=WHITE,fg=BLUE,font=("Arial",9,"italic")).grid(row=10,column=0,columnspan=2,sticky="w",padx=12,pady=6)
        note="• Lunes a sábado, 08:00–12:00\n• Intervalos normales: 30 min\n• Reparación: 1 hora continua\n• Baja: 1 vehículo; alta: hasta 3"
        tk.Label(p,text=note,justify="left",anchor="w",bg=LIGHT,fg=TEXT,font=("Arial",10),padx=10,pady=10).grid(row=11,column=0,columnspan=2,sticky="ew",padx=12,pady=8)

    def set_contacts(self,enabled):
        state="normal" if enabled else "disabled"
        for e in self.contact_entries:
            e.configure(state=state)

    def search_plate(self):
        plate=self.placa.get().strip()
        if not plate:
            self.vehicle_data=None; self.set_contacts(True); return
        v=self.db.vehicle(plate)
        self.vehicle_data=v
        if v:
            self.tipo.set(v["tipo_placa"]); self.km.set(str(v["kilometraje_actual"]))
            self.nombre.set(v["nombre"]); self.apellido.set(v["apellido"])
            self.telefono.set(v["telefono"]); self.nit.set(v["nit"] or "")
            self.correo.set(v["correo"] or ""); self.set_contacts(False)
            self.vstatus.set("Placa registrada: se reutilizan los datos del contacto.")
        else:
            self.set_contacts(True)
            for var in (self.nombre,self.apellido,self.telefono,self.nit,self.correo): var.set("")
            self.vstatus.set("Placa nueva: complete los datos del contacto.")

    def valid_date(self):
        try:
            d=datetime.strptime(self.date.get().strip(),"%Y-%m-%d")
        except ValueError:
            raise ValueError("Use fecha YYYY-MM-DD.")
        if d.weekday()==6:
            raise ValueError("No se reciben citas los domingos.")
        return d

    def refresh_slots(self):
        try:
            d=self.valid_date()
            if not self.service.get(): return
            srv=self.service_map[self.service.get()]
            slots=self.db.slots(d.strftime("%Y-%m-%d"),srv["duracion_min"])
            self.time_combo["values"]=slots
            self.time.set(slots[0] if slots else "")
            sea=self.db.season(self.date.get())
            self.season_var.set(f'{sea["nombre"]} — capacidad {sea["capacidad_por_intervalo"]}' if sea else "Temporada baja — capacidad 1")
            self.update_chief()
            self.status.set(f"{len(slots)} horario(s) disponible(s)." if slots else "No hay horarios disponibles.")
        except ValueError as e:
            self.time_combo["values"]=[]; self.time.set(""); self.status.set(str(e))

    def update_chief(self):
        if not self.agency.get() or not self.date.get(): return
        c=self.db.chief(self.agency_map[self.agency.get()],self.date.get())
        self.chief_var.set(f'Asignación automática: {c["nombre"]}' if c else "No hay jefe disponible")

    def collect(self):
        self.valid_date()
        self.search_plate()
        km=self.km.get().replace(",","").strip()
        if not self.placa.get().strip(): raise ValueError("Ingrese la placa.")
        if not km.isdigit(): raise ValueError("Kilometraje inválido.")
        if not self.service.get(): raise ValueError("Seleccione servicio.")
        if not self.agency.get(): raise ValueError("Seleccione agencia.")
        if not self.time.get(): raise ValueError("Seleccione horario.")
        if not self.vehicle_data:
            required=[("Nombre",self.nombre.get()),("Apellido",self.apellido.get()),("Teléfono",self.telefono.get()),("NIT",self.nit.get()),("Correo",self.correo.get())]
            missing=[n for n,v in required if not v.strip()]
            if missing: raise ValueError("Complete: "+", ".join(missing))
        return {"tipo":self.tipo.get(),"placa":self.placa.get().strip().upper(),"km":int(km),
                "nombre":self.nombre.get().strip(),"apellido":self.apellido.get().strip(),
                "telefono":self.telefono.get().strip(),"nit":self.nit.get().strip(),
                "correo":self.correo.get().strip(),"servicio":self.service.get(),
                "agencia":self.agency.get(),"agencia_id":self.agency_map[self.agency.get()],
                "fecha":self.date.get().strip(),"hora":self.time.get()}

    def schedule(self):
        try:
            d=self.collect()
            cid,chief,end=self.db.save(d)
            valid_email=bool(re.fullmatch(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",d["correo"]))
            notice=f'Confirmación por correo: {d["correo"]}' if valid_email else f'Confirmación por SMS: {d["telefono"]}'
            messagebox.showinfo("Cita registrada",
                f"CITA REGISTRADA CORRECTAMENTE\n\nNo. cita: {cid}\nPlaca: {d['placa']}\nServicio: {d['servicio']}\n"
                f"Agencia: {d['agencia']}\nFecha: {d['fecha']}\nHorario: {d['hora']} - {end}\n"
                f"Kilometraje: {d['km']:,} km\nJefe de taller: {chief}\n\n{notice}\n\nGuardado real en SQLite.")
            self.status.set(f"Cita #{cid} guardada en {DB_NAME.name}.")
            self.refresh_slots()
        except Exception as e:
            messagebox.showwarning("Revisar datos",str(e))

    def close_app(self):
        self.db.close()
        self.destroy()


if __name__ == "__main__":
    CarServiceApp().mainloop()
