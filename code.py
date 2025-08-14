import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import json
from datetime import datetime
from pulp import LpProblem, LpVariable, LpMinimize, LpStatus, lpSum
import pandas as pd

class ScheduleGeneratorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Enterprise Schedule Generator")
        self.root.geometry("1100x750")
        self.root.configure(bg="#f5f7fa")
        
        # General style
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.style.configure('TFrame', background='#f5f7fa')
        self.style.configure('TLabel', background='#f5f7fa', font=('Segoe UI', 11))
        self.style.configure('TButton', font=('Segoe UI', 11, 'bold'), background='#1976d2', foreground='white')
        self.style.map('TButton', background=[('active', '#1565c0')])
        self.style.configure('Header.TLabel', font=('Segoe UI', 16, 'bold'), foreground='#1976d2', background='#e3f2fd')
        self.style.configure('Treeview', font=('Segoe UI', 10), rowheight=28, background='#ffffff', fieldbackground='#ffffff')
        self.style.map('Treeview', background=[('selected', '#bbdefb')])
        self.style.configure('Treeview.Heading', font=('Segoe UI', 11, 'bold'), background='#1976d2', foreground='white')

        # Initialize generator (must be BEFORE setup_xxx_tab calls)
        self.generator = ScheduleGenerator()

        # Create tabs
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill='both', expand=True)
        self.notebook.configure(style='TNotebook')

        # Time Slots tab
        self.frame_timeslots = ttk.Frame(self.notebook, style='TFrame')
        self.notebook.add(self.frame_timeslots, text="Time Slots")
        self.setup_timeslots_tab()

        # Resources tab
        self.frame_resources = ttk.Frame(self.notebook, style='TFrame')
        self.notebook.add(self.frame_resources, text="Resources")
        self.setup_resources_tab()

        # Meetings/Events tab
        self.frame_events = ttk.Frame(self.notebook, style='TFrame')
        self.notebook.add(self.frame_events, text="Meetings/Events")
        self.setup_events_tab()

        # Constraints tab
        self.frame_constraints = ttk.Frame(self.notebook, style='TFrame')
        self.notebook.add(self.frame_constraints, text="Constraints")
        self.setup_constraints_tab()

        # Schedule tab
        self.frame_results = ttk.Frame(self.notebook, style='TFrame')
        self.notebook.add(self.frame_results, text="Schedule")
        self.setup_results_tab()

    def setup_timeslots_tab(self):
        # Title and subtitle
        header = ttk.Label(self.frame_timeslots, text="Step 1: Define Available Time Slots", style='Header.TLabel')
        header.pack(pady=(10, 0), fill='x')
        subtitle = ttk.Label(self.frame_timeslots, text="Add time slots where meetings or events can be scheduled. Example: Monday 09:00-10:00.", font=('Segoe UI', 10, 'italic'), foreground='#1976d2')
        subtitle.pack(pady=(0, 10))
        # Form
        form_frame = ttk.Frame(self.frame_timeslots)
        form_frame.pack(pady=10)
        ttk.Label(form_frame, text="Day of the week:").grid(row=0, column=0, padx=5, pady=5, sticky='e')
        self.day_var = tk.StringVar()
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
        ttk.Combobox(form_frame, textvariable=self.day_var, values=days, width=15).grid(row=0, column=1, padx=5, pady=5)
        ttk.Label(form_frame, text="Start time (ex: 09:00):").grid(row=1, column=0, padx=5, pady=5, sticky='e')
        self.start_var = tk.StringVar()
        ttk.Entry(form_frame, textvariable=self.start_var, width=10).grid(row=1, column=1, padx=5, pady=5)
        ttk.Label(form_frame, text="End time (ex: 10:00):").grid(row=2, column=0, padx=5, pady=5, sticky='e')
        self.end_var = tk.StringVar()
        ttk.Entry(form_frame, textvariable=self.end_var, width=10).grid(row=2, column=1, padx=5, pady=5)
        # Buttons
        btn_frame = ttk.Frame(self.frame_timeslots)
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text="Add Time Slot", command=self.add_timeslot).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="Delete Selection", command=self.delete_timeslot).pack(side='left', padx=5)
        # Table
        self.timeslots_tree = ttk.Treeview(self.frame_timeslots, columns=('Day', 'Start', 'End'), show='headings')
        self.timeslots_tree.heading('Day', text='Day')
        self.timeslots_tree.heading('Start', text='Start')
        self.timeslots_tree.heading('End', text='End')
        self.timeslots_tree.column('Day', width=150)
        self.timeslots_tree.column('Start', width=100)
        self.timeslots_tree.column('End', width=100)
        self.timeslots_tree.pack(fill='both', expand=True, padx=10, pady=10)
        # Summary
        self.summary_timeslots_label = ttk.Label(self.frame_timeslots, text="No time slots added yet.", font=('Segoe UI', 10, 'italic'), foreground='#388e3c')
        self.summary_timeslots_label.pack(pady=(5, 10))

    def setup_resources_tab(self):
        # Header
        header = ttk.Label(self.frame_resources, text="Step 2: Manage Enterprise Resources", style='Header.TLabel')
        header.pack(pady=10)
        # Form
        form_frame = ttk.Frame(self.frame_resources)
        form_frame.pack(pady=10)
        ttk.Label(form_frame, text="Resource name:").grid(row=0, column=0, padx=5, pady=5, sticky='e')
        self.resource_name_var = tk.StringVar()
        ttk.Entry(form_frame, textvariable=self.resource_name_var, width=20).grid(row=0, column=1, padx=5, pady=5)
        ttk.Label(form_frame, text="Resource type:").grid(row=1, column=0, padx=5, pady=5, sticky='e')
        self.resource_type_var = tk.StringVar()
        types = ['Room', 'Employee', 'Equipment', 'Other']
        ttk.Combobox(form_frame, textvariable=self.resource_type_var, values=types, width=15).grid(row=1, column=1, padx=5, pady=5)

        # Section to add availability slots to the resource
        ttk.Label(form_frame, text="Availability slots:").grid(row=2, column=0, padx=5, pady=5, sticky='ne')
        slots_frame = ttk.Frame(form_frame)
        slots_frame.grid(row=2, column=1, padx=5, pady=5, sticky='w')
        self.resource_slots = []  # Temporary list for resource slots being added

        # Fields to add a slot
        self.slot_day_var = tk.StringVar()
        self.slot_start_var = tk.StringVar()
        self.slot_end_var = tk.StringVar()
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
        ttk.Combobox(slots_frame, textvariable=self.slot_day_var, values=days, width=10).grid(row=0, column=0, padx=2)
        ttk.Entry(slots_frame, textvariable=self.slot_start_var, width=7).grid(row=0, column=1, padx=2)
        ttk.Entry(slots_frame, textvariable=self.slot_end_var, width=7).grid(row=0, column=2, padx=2)
        ttk.Button(slots_frame, text="Add this slot", command=self.add_availability_slot).grid(row=0, column=3, padx=2)

        # Table of availability slots for the resource being added
        self.availability_slots_tree = ttk.Treeview(slots_frame, columns=('Day', 'Start', 'End'), show='headings', height=3)
        self.availability_slots_tree.heading('Day', text='Day')
        self.availability_slots_tree.heading('Start', text='Start')
        self.availability_slots_tree.heading('End', text='End')
        self.availability_slots_tree.column('Day', width=70)
        self.availability_slots_tree.column('Start', width=60)
        self.availability_slots_tree.column('End', width=60)
        self.availability_slots_tree.grid(row=1, column=0, columnspan=4, pady=5)
        ttk.Button(slots_frame, text="Delete selected slot", command=self.delete_availability_slot).grid(row=2, column=0, columnspan=4, pady=2)

        # Buttons
        btn_frame = ttk.Frame(self.frame_resources)
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text="Add Resource", command=self.add_resource).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="Delete Selection", command=self.delete_resource).pack(side='left', padx=5)
        # Table
        self.resources_tree = ttk.Treeview(self.frame_resources, columns=('Name', 'Type', 'Availability'), show='headings')
        self.resources_tree.heading('Name', text='Name')
        self.resources_tree.heading('Type', text='Type')
        self.resources_tree.heading('Availability', text='Availability')
        self.resources_tree.column('Name', width=150)
        self.resources_tree.column('Type', width=120)
        self.resources_tree.column('Availability', width=250)
        self.resources_tree.pack(fill='both', expand=True, padx=10, pady=10)

    def setup_events_tab(self):
        # Header
        header = ttk.Label(self.frame_events, text="Step 3: Manage Meetings / Events", style='Header.TLabel')
        header.pack(pady=10, fill='x')
        # Form
        form_frame = ttk.Frame(self.frame_events)
        form_frame.pack(pady=10)
        ttk.Label(form_frame, text="Meeting/Event name:").grid(row=0, column=0, padx=5, pady=5, sticky='e')
        self.event_name_var = tk.StringVar()
        ttk.Entry(form_frame, textvariable=self.event_name_var, width=20).grid(row=0, column=1, padx=5, pady=5)
        ttk.Label(form_frame, text="Duration (hours):").grid(row=1, column=0, padx=5, pady=5, sticky='e')
        self.event_duration_var = tk.DoubleVar()
        ttk.Entry(form_frame, textvariable=self.event_duration_var, width=10).grid(row=1, column=1, padx=5, pady=5)
        # Resource selection (checkboxes)
        ttk.Label(form_frame, text="Required resources:").grid(row=2, column=0, padx=5, pady=5, sticky='ne')
        self.resource_checkbox_vars = []
        self.resource_checkbox_widgets = []
        self.resources_checkbox_frame = ttk.Frame(form_frame)
        self.resources_checkbox_frame.grid(row=2, column=1, padx=5, pady=5, sticky='w')
        self.update_event_resources_checkboxes()
        # Display of selected resources availability
        ttk.Label(form_frame, text="Availability of selected resources:").grid(row=3, column=0, padx=5, pady=5, sticky='ne')
        self.availability_resources_text = tk.Text(form_frame, height=4, width=40, font=('Segoe UI', 9), bg='#e3f2fd')
        self.availability_resources_text.grid(row=3, column=1, padx=5, pady=5, sticky='w')
        # Buttons
        btn_frame = ttk.Frame(self.frame_events)
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text="Add Meeting/Event", command=self.add_event).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="Delete Selection", command=self.delete_event).pack(side='left', padx=5)
        # Table
        self.events_tree = ttk.Treeview(self.frame_events, columns=('Name', 'Duration', 'Resources', 'Preferences'), show='headings')
        self.events_tree.heading('Name', text='Name')
        self.events_tree.heading('Duration', text='Duration (h)')
        self.events_tree.heading('Resources', text='Resources')
        self.events_tree.heading('Preferences', text='Preferences')
        self.events_tree.column('Name', width=150)
        self.events_tree.column('Duration', width=80)
        self.events_tree.column('Resources', width=200)
        self.events_tree.column('Preferences', width=150)
        self.events_tree.pack(fill='both', expand=True, padx=10, pady=10)

    def setup_constraints_tab(self):
        # Header
        header = ttk.Label(self.frame_constraints, text="Step 4: Manage Constraints", style='Header.TLabel')
        header.pack(pady=10)
        # Form
        form_frame = ttk.Frame(self.frame_constraints)
        form_frame.pack(pady=10)
        ttk.Label(form_frame, text="Placement preference:").grid(row=0, column=0, padx=5, pady=5, sticky='e')
        self.constraint_type_var = tk.StringVar()
        types = ['Prefer early in the day', 'Prefer late in the day', 'No preference']
        ttk.Combobox(form_frame, textvariable=self.constraint_type_var, values=types, width=30).grid(row=0, column=1, padx=5, pady=5)
        # Help message
        self.constraint_help_label = ttk.Label(form_frame, text="This preference will be applied to all events during schedule generation.", foreground='#1976d2', font=('Segoe UI', 9, 'italic'))
        self.constraint_help_label.grid(row=1, column=0, columnspan=2, padx=5, pady=5)
        # Buttons
        btn_frame = ttk.Frame(self.frame_constraints)
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text="Add Constraint", command=self.add_constraint).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="Delete Selection", command=self.delete_constraint).pack(side='left', padx=5)
        # Table
        self.constraints_tree = ttk.Treeview(self.frame_constraints, columns=('Type',), show='headings')
        self.constraints_tree.heading('Type', text='Placement Preference')
        self.constraints_tree.column('Type', width=300)
        self.constraints_tree.pack(fill='both', expand=True, padx=10, pady=10)

    def setup_results_tab(self):
        # Header
        header = ttk.Label(self.frame_results, text="Generated Enterprise Schedule", style='Header.TLabel')
        header.pack(pady=10)
        # Buttons
        btn_frame = ttk.Frame(self.frame_results)
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text="Generate Schedule", command=self.generate_schedule).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="Export to Excel", command=self.export_excel).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="Show JSON", command=self.show_json).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="Show Calendar", command=self.show_calendar).pack(side='left', padx=5)
        # Results table
        self.results_tree = ttk.Treeview(self.frame_results, columns=('Event', 'Day', 'Start', 'End', 'Resource'), show='headings')
        self.results_tree.heading('Event', text='Meeting/Event')
        self.results_tree.heading('Day', text='Day')
        self.results_tree.heading('Start', text='Start')
        self.results_tree.heading('End', text='End')
        self.results_tree.heading('Resource', text='Resource')
        self.results_tree.column('Event', width=200)
        self.results_tree.column('Day', width=100)
        self.results_tree.column('Start', width=80)
        self.results_tree.column('End', width=80)
        self.results_tree.column('Resource', width=150)
        self.results_tree.pack(fill='both', expand=True, padx=10, pady=10)
        # JSON text area
        self.json_text = tk.Text(self.frame_results, height=10, wrap='word')
        scrollbar = ttk.Scrollbar(self.frame_results, orient='vertical', command=self.json_text.yview)
        self.json_text.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side='right', fill='y')
        self.json_text.pack(fill='both', expand=True, padx=10, pady=10)
        self.json_text.pack_forget()  # Hidden by default
        # Calendar canvas (hidden by default)
        self.cal_canvas = tk.Canvas(self.frame_results, width=900, height=400, bg='#f5f7fa', highlightthickness=0)
        self.cal_canvas.pack(pady=10)
        self.cal_canvas.pack_forget()

    # --- Methods to handle interactions ---
    def add_timeslot(self):
        day = self.day_var.get()
        start = self.start_var.get()
        end = self.end_var.get()
        if not day or not start or not end:
            messagebox.showerror("Error", "Please fill all time slot fields.")
            return
        self.generator.timeslots.append({'day': day, 'start': start, 'end': end})
        self.timeslots_tree.insert('', 'end', values=(day, start, end))
        self.day_var.set('')
        self.start_var.set('')
        self.end_var.set('')
        messagebox.showinfo("Time slot added", f"✅ Time slot {day} {start}-{end} added.")
        self.update_summary_timeslots()

    def delete_timeslot(self):
        selected = self.timeslots_tree.selection()
        for item in selected:
            values = self.timeslots_tree.item(item, 'values')
            self.generator.timeslots = [c for c in self.generator.timeslots if not (c['day'] == values[0] and c['start'] == values[1] and c['end'] == values[2])]
            self.timeslots_tree.delete(item)
        self.update_summary_timeslots()

    def update_summary_timeslots(self):
        n = len(self.generator.timeslots)
        if n == 0:
            self.summary_timeslots_label.config(text="No time slots added yet.")
        else:
            summary = ", ".join([f"{c['day']} {c['start']}-{c['end']}" for c in self.generator.timeslots])
            self.summary_timeslots_label.config(text=f"You have added {n} time slot(s): {summary}")

    def add_availability_slot(self):
        day = self.slot_day_var.get()
        start = self.slot_start_var.get()
        end = self.slot_end_var.get()
        if not day or not start or not end:
            messagebox.showerror("Error", "Please fill all availability slot fields.")
            return
        slot = {'day': day, 'start': start, 'end': end}
        self.resource_slots.append(slot)
        self.availability_slots_tree.insert('', 'end', values=(day, start, end))
        self.slot_day_var.set('')
        self.slot_start_var.set('')
        self.slot_end_var.set('')

    def delete_availability_slot(self):
        selected = self.availability_slots_tree.selection()
        for item in selected:
            values = self.availability_slots_tree.item(item, 'values')
            self.resource_slots = [c for c in self.resource_slots if not (c['day'] == values[0] and c['start'] == values[1] and c['end'] == values[2])]
            self.availability_slots_tree.delete(item)

    def add_resource(self):
        name = self.resource_name_var.get()
        type_ = self.resource_type_var.get()
        if not name or not type_ or not self.resource_slots:
            messagebox.showerror("Error", "Please fill all fields and add at least one availability slot.")
            return
        self.generator.resources.append({'name': name, 'type': type_, 'availability': list(self.resource_slots)})
        availability_str = ", ".join([f"{c['day']} {c['start']}-{c['end']}" for c in self.resource_slots])
        self.resources_tree.insert('', 'end', values=(name, type_, availability_str))
        self.resource_name_var.set('')
        self.resource_type_var.set('')
        self.resource_slots.clear()
        for i in self.availability_slots_tree.get_children():
            self.availability_slots_tree.delete(i)
        # Update resource list in events tab
        if hasattr(self, 'update_event_resources_checkboxes'):
            self.update_event_resources_checkboxes()

    def delete_resource(self):
        selected = self.resources_tree.selection()
        for item in selected:
            values = self.resources_tree.item(item, 'values')
            self.generator.resources = [r for r in self.generator.resources if not (r['name'] == values[0] and r['type'] == values[1] and ", ".join([f"{c['day']} {c['start']}-{c['end']}" for c in r['availability']]) == values[2])]
            self.resources_tree.delete(item)
        # Update resource list in events tab
        if hasattr(self, 'update_event_resources_checkboxes'):
            self.update_event_resources_checkboxes()

    def update_event_resources_checkboxes(self):
        # Clear old checkboxes
        for widget in getattr(self, 'resource_checkbox_widgets', []):
            widget.destroy()
        self.resource_checkbox_vars = []
        self.resource_checkbox_widgets = []
        # Add a checkbox for each resource
        if not self.generator.resources:
            label = ttk.Label(self.resources_checkbox_frame, text="Add resources first in the Resources tab.", foreground='#d32f2f', font=('Segoe UI', 10, 'italic'))
            label.grid(row=0, column=0, sticky='w')
            self.resource_checkbox_widgets.append(label)
        else:
            for idx, r in enumerate(self.generator.resources):
                var = tk.BooleanVar()
                cb = ttk.Checkbutton(self.resources_checkbox_frame, text=f"{r['name']} ({r['type']})", variable=var, command=self.show_selected_resources_availability)
                cb.grid(row=idx, column=0, sticky='w')
                self.resource_checkbox_vars.append(var)
                self.resource_checkbox_widgets.append(cb)

    def show_selected_resources_availability(self):
        self.availability_resources_text.delete('1.0', tk.END)
        for idx, var in enumerate(self.resource_checkbox_vars):
            if var.get():
                r = self.generator.resources[idx]
                availability = ", ".join([f"{c['day']} {c['start']}-{c['end']}" for c in r['availability']])
                self.availability_resources_text.insert(tk.END, f"{r['name']}: {availability}\n")

    def add_event(self):
        name = self.event_name_var.get()
        duration = self.event_duration_var.get()
        resources = [self.generator.resources[i]['name'] for i, var in enumerate(self.resource_checkbox_vars) if var.get()]
        if not name or not duration or not resources:
            messagebox.showerror("Error", "Please fill all fields and select at least one resource.")
            return
        self.generator.events.append({'name': name, 'duration': duration, 'resources': resources})
        self.events_tree.insert('', 'end', values=(name, duration, ", ".join(resources), ""))
        self.event_name_var.set('')
        self.event_duration_var.set(0)
        for var in self.resource_checkbox_vars:
            var.set(False)
        self.availability_resources_text.delete('1.0', tk.END)

    def delete_event(self):
        selected = self.events_tree.selection()
        for item in selected:
            values = self.events_tree.item(item, 'values')
            self.generator.events = [e for e in self.generator.events if not (e['name'] == values[0] and str(e['duration']) == str(values[1]))]
            self.events_tree.delete(item)

    def add_constraint(self):
        type_ = self.constraint_type_var.get()
        if not type_:
            messagebox.showerror("Error", "Please choose a placement preference.")
            return
        self.generator.constraints.append({'type': type_})
        self.constraints_tree.insert('', 'end', values=(type_,))
        self.constraint_type_var.set('')

    def delete_constraint(self):
        selected = self.constraints_tree.selection()
        for item in selected:
            values = self.constraints_tree.item(item, 'values')
            self.generator.constraints = [c for c in self.generator.constraints if c['type'] != values[0]]
            self.constraints_tree.delete(item)

    def generate_schedule(self):
        results, alerts = self.generator.generate()
        for i in self.results_tree.get_children():
            self.results_tree.delete(i)
        for r in results:
            self.results_tree.insert('', 'end', values=(r['event'], r['day'], r['start'], r['end'], r['resource']))
        self.results = results
        self.json_text.pack_forget()
        self.cal_canvas.pack_forget() if hasattr(self, 'cal_canvas') else None
        if alerts:
            messagebox.showwarning("Unplanned Events", "\n".join(alerts))

    def export_excel(self):
        if not hasattr(self, 'results') or not self.results:
            messagebox.showerror("Error", "No results to export.")
            return
        df = pd.DataFrame(self.results)
        file = filedialog.asksaveasfilename(defaultextension='.xlsx', filetypes=[('Excel files', '*.xlsx')])
        if file:
            df.to_excel(file, index=False)
            messagebox.showinfo("Success", "Export successful!")

    def show_json(self):
        if not hasattr(self, 'results') or not self.results:
            messagebox.showerror("Error", "No results to display.")
            return
        self.json_text.delete('1.0', tk.END)
        self.json_text.insert(tk.END, json.dumps(self.results, indent=2, ensure_ascii=False))
        self.json_text.pack(fill='both', expand=True, padx=10, pady=10)

    def show_calendar(self):
        # Hide JSON
        self.json_text.pack_forget()
        # Clear canvas
        self.cal_canvas.delete('all')
        self.cal_canvas.pack(fill='both', expand=True, padx=10, pady=10)
        # Prepare grid
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
        hours = [f"{h:02d}:00" for h in range(8, 19)]  # 8h to 18h
        cell_w = 120
        cell_h = 35
        x0, y0 = 80, 40
        # Day headers
        for j, day in enumerate(days):
            self.cal_canvas.create_rectangle(x0 + j*cell_w, y0 - cell_h, x0 + (j+1)*cell_w, y0, fill='#1976d2', outline='white')
            self.cal_canvas.create_text(x0 + j*cell_w + cell_w/2, y0 - cell_h/2, text=day, fill='white', font=('Segoe UI', 11, 'bold'))
        # Hour headers
        for i, hour in enumerate(hours):
            self.cal_canvas.create_rectangle(x0 - 80, y0 + i*cell_h, x0, y0 + (i+1)*cell_h, fill='#e3f2fd', outline='white')
            self.cal_canvas.create_text(x0 - 40, y0 + i*cell_h + cell_h/2, text=hour, fill='#1976d2', font=('Segoe UI', 10, 'bold'))
        # Grid
        for j in range(len(days)):
            for i in range(len(hours)):
                self.cal_canvas.create_rectangle(x0 + j*cell_w, y0 + i*cell_h, x0 + (j+1)*cell_w, y0 + (i+1)*cell_h, fill='#ffffff', outline='#bbdefb')
        # Place events
        colors = ['#90caf9', '#a5d6a7', '#ffe082', '#f48fb1', '#ce93d8', '#ffab91', '#b0bec5']
        if not hasattr(self, 'results') or not self.results:
            return
        for idx, evt in enumerate(self.results):
            if evt['day'] not in days:
                continue
            try:
                col = days.index(evt['day'])
                start_h = int(evt['start'].split(':')[0])
                end_h = int(evt['end'].split(':')[0])
                row_start = start_h - 8
                row_end = end_h - 8
                color = colors[idx % len(colors)]
                self.cal_canvas.create_rectangle(x0 + col*cell_w + 2, y0 + row_start*cell_h + 2, x0 + (col+1)*cell_w - 2, y0 + row_end*cell_h - 2, fill=color, outline='#1976d2', width=2)
                txt = f"{evt['event']}\n{evt['resource']}\n{evt['start']}-{evt['end']}"
                self.cal_canvas.create_text(x0 + col*cell_w + cell_w/2, y0 + (row_start+row_end)*cell_h/2, text=txt, font=('Segoe UI', 9, 'bold'), fill='#263238')
            except Exception:
                continue

class ScheduleGenerator:
    def __init__(self):
        self.timeslots = []
        self.resources = []
        self.events = []
        self.constraints = []

    def generate(self):
        # Generation: assign each event to consecutive slots where all resources are available
        results = []
        alerts = []
        used_slots = set()
        
        # Split work slots into 1-hour slots
        slots_1h = []
        for slot in self.timeslots:
            start_h = int(slot['start'].split(':')[0])
            end_h = int(slot['end'].split(':')[0])
            for h in range(start_h, end_h):
                slots_1h.append({
                    'day': slot['day'],
                    'start': f"{h:02d}:00",
                    'end': f"{h+1:02d}:00"
                })
        
        # Determine placement preference
        preference = "none"
        if self.constraints:
            constraint = self.constraints[0]['type']
            if "early" in constraint:
                preference = "early"
            elif "late" in constraint:
                preference = "late"
        
        for evt in self.events:
            event_duration = int(evt['duration'])  # Duration in hours
            found = False
            candidates = []
            
            # Look for consecutive slots of the required duration
            for i in range(len(slots_1h) - event_duration + 1):
                consecutive_slots = slots_1h[i:i+event_duration]
                
                # Check that all consecutive slots are available for all resources
                ok = True
                for slot in consecutive_slots:
                    for resource_name in evt['resources']:
                        r = next((r for r in self.resources if r['name'] == resource_name), None)
                        if not r:
                            ok = False
                            break
                        # Check if resource is available on this slot OR if the slot is within its availability period
                        available = False
                        for avail_slot in r['availability']:
                            if avail_slot['day'] == slot['day']:
                                avail_start = int(avail_slot['start'].split(':')[0])
                                avail_end = int(avail_slot['end'].split(':')[0])
                                slot_start = int(slot['start'].split(':')[0])
                                slot_end = int(slot['end'].split(':')[0])
                                # The slot must be included in the availability
                                if slot_start >= avail_start and slot_end <= avail_end:
                                    available = True
                                    break
                        if not available:
                            ok = False
                            break
                    if not ok:
                        break
                
                # Check that these slots are not already used
                if ok:
                    for slot in consecutive_slots:
                        if (slot['day'], slot['start'], slot['end']) in used_slots:
                            ok = False
                            break
                
                if ok:
                    candidates.append(consecutive_slots)
            
            # Choose the best candidate according to preference
            if candidates:
                if preference == "early":
                    # Take the first candidate (earliest)
                    consecutive_slots = candidates[0]
                elif preference == "late":
                    # Take the last candidate (latest)
                    consecutive_slots = candidates[-1]
                else:
                    # Take the first available candidate
                    consecutive_slots = candidates[0]
                
                # Place the event
                first_slot = consecutive_slots[0]
                last_slot = consecutive_slots[-1]
                for resource_name in evt['resources']:
                    results.append({
                        'event': evt['name'],
                        'day': first_slot['day'],
                        'start': first_slot['start'],
                        'end': last_slot['end'],
                        'resource': resource_name
                    })
                # Mark all slots as used
                for slot in consecutive_slots:
                    used_slots.add((slot['day'], slot['start'], slot['end']))
                found = True
            
            if not found:
                alerts.append(f"Unable to schedule '{evt['name']}' ({evt['duration']}h): not enough consecutive slots available for all resources.")
        
        return results, alerts

if __name__ == "__main__":
    root = tk.Tk()
    app = ScheduleGeneratorApp(root)
    root.mainloop()