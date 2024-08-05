import tkinter as tk
from tkinter import ttk, simpledialog, messagebox
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from collections import defaultdict, deque

class EditableTreeview(ttk.Treeview):
    def __init__(self, master=None, **kwargs):
        super().__init__(master, **kwargs)
        self.configure(style='Custom.Treeview')
        self.bind('<Double-1>', self.on_double_click)
        self.entry = None
        self.editing_item = None
        self.editing_col = None

    def on_double_click(self, event):
        item = self.identify_row(event.y)
        col = self.identify_column(event.x)
        col = col.split('#')[-1]
        col = int(col) - 1
        
        if col >= 0:
            self.start_edit(item, col)

    def start_edit(self, item, col):
        if self.entry:
            self.entry.destroy()
        
        self.editing_item = item
        self.editing_col = col

        x, y, width, height = self.bbox(item, column=col)
        value = self.item(item, 'values')[col]

        self.entry = tk.Entry(self, validate='key', font=('Arial', 12))
        self.entry.insert(0, value)
        self.entry.place(x=x, y=y, width=width, height=height)
        self.entry.focus_set()
        self.entry.bind('<Return>', lambda e: self.save_edit())
        self.entry.bind('<FocusOut>', lambda e: self.cancel_edit())

    def save_edit(self):
        new_value = self.entry.get()
        values = list(self.item(self.editing_item, 'values'))
        values[self.editing_col] = new_value
        self.item(self.editing_item, values=values)
        self.entry.destroy()
        self.entry = None

    def cancel_edit(self):
        if self.entry:
            self.entry.destroy()
            self.entry = None

    def get_data(self):
        data = []
        for child in self.get_children():
            item = self.item(child)
            data.append(item['values'])
        return data

    def add_task(self, task_data):
        self.insert('', 'end', values=task_data)

    def delete_selected_task(self):
        selected_item = self.selection()
        if selected_item:
            self.delete(selected_item)

    def get_task_dependencies(self, task_name):
        dependencies = set()
        for item in self.get_children():
            task, depends, _, _, _, _, _ = self.item(item, 'values')
            if task_name in depends.split(', '):
                dependencies.add(task)
        return dependencies

# Style configuration for Treeview
style = ttk.Style()
style.configure('Custom.Treeview',
                background='#f5f5f5',
                foreground='#333333',
                fieldbackground='#e6e6e6',
                font=('Arial', 11))

style.configure('Custom.Treeview.Heading',
                background='#4a4a4a',
                foreground='#ffffff',
                font=('Arial', 12, 'bold'))

style.configure('Custom.Treeview.Cell',
                background='#ffffff',
                foreground='#333333',
                borderwidth=1,
                relief='solid')

def calculate_critical_path(tasks):
    task_dict = {
        task: {
            'depends': depends.split(', ') if depends != '-' else [],
            'duration': int(duration)
        }
        for task, depends, duration, _, _, _, _ in tasks
    }

    start_dates = {}
    end_dates = {}
    indegrees = defaultdict(int)
    adj_list = defaultdict(list)

    for task, info in task_dict.items():
        for dep in info['depends']:
            adj_list[dep].append(task)
            indegrees[task] += 1

    zero_indegree_queue = deque([task for task in task_dict if indegrees[task] == 0])
    topo_order = []

    while zero_indegree_queue:
        task = zero_indegree_queue.popleft()
        topo_order.append(task)

        for neighbor in adj_list[task]:
            indegrees[neighbor] -= 1
            if indegrees[neighbor] == 0:
                zero_indegree_queue.append(neighbor)

    for task in topo_order:
        if task_dict[task]['depends']:
            start_dates[task] = max(end_dates[dep] for dep in task_dict[task]['depends'])
        else:
            start_dates[task] = 0
        end_dates[task] = start_dates[task] + task_dict[task]['duration']

    # Initialize LF and LS
    latest_finish = {task: end_dates[task] for task in end_dates}
    latest_start = {task: end_dates[task] - task_dict[task]['duration'] for task in end_dates}

    for task in reversed(topo_order):
        for successor in adj_list[task]:
            latest_finish[task] = min(latest_finish[task], latest_start[successor])
        latest_start[task] = latest_finish[task] - task_dict[task]['duration']

    # Critical Path Calculation
    critical_path = []
    end_time = max(end_dates.values())
    for task in topo_order[::-1]:
        if end_dates[task] == end_time:
            critical_path.append(task)
            end_time -= task_dict[task]['duration']

    critical_path.reverse()
    
    return critical_path, max(end_dates.values())

def draw_gantt_chart(tasks, critical_path):
    df = pd.DataFrame(tasks, columns=['Task', 'Task phụ thuộc', 'Duration', 'ES', 'EF', 'LS', 'LF'])

    gantt_data = []
    start_dates = {}

    for task, depends, duration, _, _, _, _ in tasks:
        duration = int(duration)
        if depends == '-':
            start_date = 0
        else:
            depends_tasks = depends.split(', ')
            start_date = max(start_dates.get(dep, 0) for dep in depends_tasks)

        end_date = start_date + duration
        gantt_data.append({
            'Task': task,
            'Start': start_date,
            'Finish': end_date
        })
        start_dates[task] = end_date

    df_gantt = pd.DataFrame(gantt_data)

    fig, ax = plt.subplots(figsize=(10, 6))  # Adjusted figure size

    for i, row in df_gantt.iterrows():
        color = 'red' if row['Task'] in critical_path else '#6a5acd'
        edgecolor = 'black' if row['Task'] in critical_path else 'gray'
        ax.barh(row['Task'], row['Finish'] - row['Start'], left=row['Start'], color=color, edgecolor=edgecolor, height=0.4)

    ax.set_xlabel('Time')
    ax.set_ylabel('Task')
    ax.set_title('Gantt Chart of Tasks')

    ax.grid(True, linestyle='--', alpha=0.5)
    for i, row in df_gantt.iterrows():
        ax.text(row['Start'] + (row['Finish'] - row['Start']) / 2, i, row['Task'],
                ha='center', va='center', color='black', weight='bold')

    plt.tight_layout()

    # Clear the previous plot before drawing a new one
    for widget in plot_frame.winfo_children():
        widget.destroy()

    canvas = FigureCanvasTkAgg(fig, master=plot_frame)
    canvas.draw()
    canvas.get_tk_widget().pack(fill='both', expand=True, padx=10, pady=10)

def find_earliest_latest_start_finish(tasks):
    task_dict = {
        task: {
            'depends': depends.split(', ') if depends != '-' else [],
            'duration': int(duration)
        }
        for task, depends, duration, _, _, _, _ in tasks
    }

    start_dates = {}
    end_dates = {}
    latest_start = {}
    latest_finish = {}
    indegrees = defaultdict(int)
    adj_list = defaultdict(list)

    for task, info in task_dict.items():
        for dep in info['depends']:
            adj_list[dep].append(task)
            indegrees[task] += 1

    zero_indegree_queue = deque([task for task in task_dict if indegrees[task] == 0])
    topo_order = []

    while zero_indegree_queue:
        task = zero_indegree_queue.popleft()
        topo_order.append(task)

        for neighbor in adj_list[task]:
            indegrees[neighbor] -= 1
            if indegrees[neighbor] == 0:
                zero_indegree_queue.append(neighbor)

    for task in topo_order:
        if task_dict[task]['depends']:
            start_dates[task] = max(end_dates[dep] for dep in task_dict[task]['depends'])
        else:
            start_dates[task] = 0
        end_dates[task] = start_dates[task] + task_dict[task]['duration']

    # Initialize LF and LS
    latest_finish = {task: end_dates[task] for task in end_dates}
    latest_start = {task: end_dates[task] - task_dict[task]['duration'] for task in end_dates}

    for task in reversed(topo_order):
        for successor in adj_list[task]:
            latest_finish[task] = min(latest_finish[task], latest_start[successor])
        latest_start[task] = latest_finish[task] - task_dict[task]['duration']

    return start_dates, end_dates, latest_start, latest_finish

def on_calculate_and_draw():
    tasks = table.get_data()
    if not tasks:
        return

    start_dates, end_dates, latest_start, latest_finish = find_earliest_latest_start_finish(tasks)
    critical_path, longest_duration = calculate_critical_path(tasks)

    for i, task in enumerate(tasks):
        task_name = task[0]
        es = start_dates.get(task_name, 'N/A')
        ef = end_dates.get(task_name, 'N/A')
        ls = latest_start.get(task_name, 'N/A')
        lf = latest_finish.get(task_name, 'N/A')
        
        table.item(table.get_children()[i], values=(
            task_name,
            task[1],  # Dependencies
            task[2],  # Duration
            es,
            ef,
            ls,
            lf
        ))

    critical_path_label.config(text=f"Critical Path: {' -> '.join(critical_path)}")
    duration_label.config(text=f"Duration dài nhất của dự án: {longest_duration} ngày")

    draw_gantt_chart(tasks, critical_path)

def add_task():
    def save_task():
        task_name = entry_task_name.get()
        dependencies = entry_dependencies.get()
        duration = entry_duration.get()

        if not task_name or not duration:
            messagebox.showwarning("Input Error", "Please provide all required fields")
            return

        try:
            duration = int(duration)
        except ValueError:
            messagebox.showwarning("Input Error", "Duration must be an integer")
            return

        table.add_task((task_name, dependencies if dependencies else '-', duration, '', '', '', ''))
        add_task_window.destroy()
        on_calculate_and_draw()

    add_task_window = tk.Toplevel(root)
    add_task_window.title("Add Task")

    tk.Label(add_task_window, text="Task Name:").grid(row=0, column=0, padx=10, pady=5)
    entry_task_name = tk.Entry(add_task_window)
    entry_task_name.grid(row=0, column=1, padx=10, pady=5)

    tk.Label(add_task_window, text="Dependencies (comma separated):").grid(row=1, column=0, padx=10, pady=5)
    entry_dependencies = tk.Entry(add_task_window)
    entry_dependencies.grid(row=1, column=1, padx=10, pady=5)

    tk.Label(add_task_window, text="Duration:").grid(row=2, column=0, padx=10, pady=5)
    entry_duration = tk.Entry(add_task_window)
    entry_duration.grid(row=2, column=1, padx=10, pady=5)

    tk.Button(add_task_window, text="Save", command=save_task).grid(row=3, column=0, columnspan=2, pady=10)

def delete_task():
    selected_items = table.selection()
    if not selected_items:
        messagebox.showwarning("No Selection", "Please select a task to delete")
        return

    for item in selected_items:
        task_name = table.item(item, 'values')[0]
        if table.get_task_dependencies(task_name):
            messagebox.showwarning("Cannot Delete", f"Task '{task_name}' cannot be deleted because it is a dependency for other tasks.")
            return

    table.delete(selected_items)
    on_calculate_and_draw()

# Create the main window
root = tk.Tk()
root.title("Project Management")

# Create frames for layout
frame = tk.Frame(root)
frame.grid(row=0, column=0, sticky='nsew')

plot_frame = tk.Frame(root)
plot_frame.grid(row=1, column=0, sticky='nsew')

# Create labels
critical_path_label = tk.Label(root, text="Critical Path:")
critical_path_label.grid(row=2, column=0, sticky='w', padx=10, pady=5)

duration_label = tk.Label(root, text="Duration dài nhất của dự án:")
duration_label.grid(row=3, column=0, sticky='w', padx=10, pady=5)

# Create Treeview
columns = ('Task', 'Task phụ thuộc', 'Duration', 'ES', 'EF', 'LS', 'LF')
table = EditableTreeview(frame, columns=columns, show='headings')
table.grid(row=0, column=0, sticky='nsew')

for col in columns:
    table.heading(col, text=col)
    table.column(col, width=150, anchor='w')

# Add sample data (optional)
tasks = [
    ('Task 1', '-', 5, '', '', '', ''),
    ('Task 2', 'Task 1', 3, '', '', '', ''),
    ('Task 3', 'Task 1', 2, '', '', '', ''),
    ('Task 4', 'Task 2, Task 3', 4, '', '', '', '')
]

for task in tasks:
    table.insert('', 'end', values=task)

# Create buttons
button_frame = tk.Frame(root)
button_frame.grid(row=4, column=0, pady=10, sticky='ew')

calculate_button = tk.Button(button_frame, text="Calculate and Draw", command=on_calculate_and_draw)
calculate_button.grid(row=0, column=0, padx=10)

add_task_button = tk.Button(button_frame, text="Add Task", command=add_task)
add_task_button.grid(row=0, column=1, padx=10)

delete_task_button = tk.Button(button_frame, text="Delete Task", command=delete_task)
delete_task_button.grid(row=0, column=2, padx=10)

# Run the Tkinter event loop
root.mainloop()
