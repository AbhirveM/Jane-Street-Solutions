import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import random
import json
import csv
import os

class GridCell:
    def __init__(self):
        self.value = ""      # Current displayed value (1-9)
        self.region = None   # Region number (1-99)
        self.tile = False    # Black tile status
        self.yellow = False  # Protected cell status
        self.original_value = ""  # Original value before increments
        self.increment_value = 0  # Total increments received
        self.contributing_tiles = set()  # Coordinates of tiles that contributed increments
    
    def to_dict(self):
        return {
            'value': self.value,
            'region': self.region,
            'tile': self.tile,
            'yellow': self.yellow,
            'original_value': self.original_value,
            'increment_value': self.increment_value,
            'contributing_tiles': list(self.contributing_tiles)
        }
    
    @classmethod
    def from_dict(cls, data):
        cell = cls()
        cell.value = data['value']
        cell.region = data['region']
        cell.tile = data['tile']
        cell.yellow = data['yellow']
        cell.original_value = data.get('original_value', '')
        cell.increment_value = data.get('increment_value', 0)
        cell.contributing_tiles = set(data.get('contributing_tiles', []))
        return cell

    def to_list(self):
        # Convert region None to empty string for CSV
        region_str = "" if self.region is None else str(self.region)
        return [
            self.value,
            region_str,
            "1" if self.tile else "0",
            "1" if self.yellow else "0",
            self.original_value,
            str(self.increment_value),
            ",".join(str(x) for x in self.contributing_tiles)
        ]
    
    @classmethod
    def from_list(cls, data):
        cell = cls()
        cell.value = data[0]
        cell.region = None if data[1] == "" else int(data[1])
        cell.tile = data[2] == "1"
        cell.yellow = data[3] == "1"
        cell.original_value = data[4] if len(data) > 4 else ""
        cell.increment_value = int(data[5]) if len(data) > 5 and data[5] else 0
        cell.contributing_tiles = set(data[6].split(",")) if len(data) > 6 and data[6] else set()
        return cell

class LogicPuzzleGrid:
    def __init__(self, root):
        self.root = root
        self.root.title("Jane Street Puzzle")

        # Grid size
        self.grid_size = 11
        
        # Initialize the grid data structure
        self.grid_data = [[GridCell() for _ in range(self.grid_size)] for _ in range(self.grid_size)]
        
        # Fixed row labels
        self.row_labels = [
            "Square",
            "Product of Digits is 20",
            "Multiple of 13",
            "Multiple of 32",
            "Divisible by Each of its Digits",
            "Product of Digits is 25",
            "Divisible by Each of its Digits",
            "Odd and a Palindrome",
            "Fibonacci",
            "Product of Digits is 2025",
            "Prime"
        ]
        
        # Track selected cells and mode
        self.selected_cells = set()  # Store multiple selected cells
        self.selection_start = None  # For drag selection
        self.editor_mode = False  # Start in solve mode
        
        # For handling region number input
        self.current_region_input = ""
        self.region_input_timer = None
        
        # For tile placement and increments
        self.placing_tile = False
        self.tile_position = None
        self.displaced_value = 0
        self.remaining_increments = 0
        self.increment_buttons = [] 
        
        # Store region colors for consistent visualization
        self.region_colors = {}
        
        self.setup_ui()
        self.bind_events()
        
    def setup_ui(self):
        # Main container
        self.main_container = ttk.Frame(self.root, padding="10")
        self.main_container.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Get system background color
        style = ttk.Style()
        bg_color = style.lookup('TFrame', 'background')
        
        # Top control panel
        self.control_panel = ttk.Frame(self.main_container, padding="5")
        self.control_panel.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E))
        
        # Mode toggle button
        self.mode_var = tk.StringVar(value="Solve Mode")  # Initialize in solve mode
        self.mode_button = ttk.Button(self.control_panel, textvariable=self.mode_var,
                                    command=self.toggle_mode)
        self.mode_button.pack(side=tk.LEFT, padx=5)
        
        # Clear selection button
        self.clear_sel_button = ttk.Button(self.control_panel, text="Clear Selection",
                                         command=self.clear_selection)
        self.clear_sel_button.pack(side=tk.LEFT, padx=5)
        
        # Save button
        self.save_button = ttk.Button(self.control_panel, text="Save Layout",
                                    command=self.save_layout)
        self.save_button.pack(side=tk.LEFT, padx=5)
        
        # Load button
        self.load_button = ttk.Button(self.control_panel, text="Load Layout",
                                    command=self.load_layout)
        self.load_button.pack(side=tk.LEFT, padx=5)
        
        # Total sum label
        self.total_sum_var = tk.StringVar(value="Total Sum: 0")
        self.total_sum_label = ttk.Label(self.control_panel, textvariable=self.total_sum_var,
                                       font=('Arial', 12, 'bold'))
        self.total_sum_label.pack(side=tk.RIGHT, padx=20)
        
        # Instructions label
        self.editor_instructions = "Editor Mode: Click/Drag to select, Numbers=Region, Y=Yellow, R=Remove Region, Backspace=Clear"
        self.solve_instructions = "Solve Mode: Select cells and type 1-9 to enter numbers, T=Place/Remove Tile, Backspace=Clear"
        self.instructions = ttk.Label(self.control_panel, text=self.solve_instructions)  # Show solve mode instructions
        self.instructions.pack(side=tk.LEFT, padx=20)
        
        # Canvas for drawing the grid
        self.canvas_size = 550
        self.cell_size = self.canvas_size // self.grid_size
        
        # Add padding for the grid
        self.grid_padding = 10  # Pixels of padding around the grid
        canvas_with_padding = self.canvas_size + (2 * self.grid_padding)
        
        # Row labels container (left)
        label_container = tk.Frame(self.main_container, bg=bg_color)
        label_container.grid(row=1, column=0, padx=(0, 5))
        
        # Row labels
        for i in range(self.grid_size):
            label = tk.Label(
                label_container,
                text=self.row_labels[i],
                font=('Arial', 10),
                fg='#444444',
                bg=bg_color,
                anchor='w',
                width=25
            )
            # Position label to align with grid cells
            y_position = (i * self.cell_size) + (self.cell_size // 2) + self.grid_padding
            label.place(x=0, y=y_position, anchor='w')
        
        # Set the container size to match the grid
        label_container.configure(width=200, height=canvas_with_padding)
        
        # Canvas (right of labels)
        self.canvas = tk.Canvas(
            self.main_container,
            width=canvas_with_padding,
            height=canvas_with_padding,
            background=bg_color
        )
        self.canvas.grid(row=1, column=1)
        
        # Draw initial grid
        self.draw_grid()
    
    def toggle_mode(self):
        self.editor_mode = not self.editor_mode
        print(f"Switched to {'Editor' if self.editor_mode else 'Solve'} mode")
        self.mode_var.set("Editor Mode" if self.editor_mode else "Solve Mode")
        self.instructions.config(
            text=self.editor_instructions if self.editor_mode else self.solve_instructions
        )
        
        self.selected_cells.clear()
        self.current_region_input = ""
        self.draw_grid()
    
    def bind_events(self):
        self.canvas.bind('<Button-1>', self.on_mouse_down)
        self.canvas.bind('<B1-Motion>', self.on_mouse_drag)
        self.canvas.bind('<ButtonRelease-1>', self.on_mouse_up)
        self.canvas.bind('<Shift-Button-1>', self.on_shift_click)
        self.root.bind('<Key>', self.on_key)
        self.root.bind('<BackSpace>', self.on_backspace)
        self.root.bind('<Return>', self.on_enter)
    
    def get_cell_coords(self, event):
        # Ensure we're getting coordinates relative to the canvas
        canvas_x = self.canvas.canvasx(event.x)
        canvas_y = self.canvas.canvasy(event.y)
        
        # Convert to grid coordinates
        col = int(canvas_x // self.cell_size)
        row = int(canvas_y // self.cell_size)
        
        # Validate coordinates are within grid bounds
        if 0 <= row < self.grid_size and 0 <= col < self.grid_size:
            return (row, col)
        return None
    
    def clear_selection(self):
        self.selected_cells.clear()
        self.draw_grid()
    
    def is_valid_region_shape(self, cells):
        # Remove the straight line restriction - all shapes are valid
        return True
    
    def is_contiguous(self, cells):
        if not cells:
            return True
            
        # Check if cells are connected
        cells = set(cells)
        visited = set()
        to_visit = {next(iter(cells))}
        
        while to_visit:
            current = to_visit.pop()
            visited.add(current)
            row, col = current
            
            # Check adjacent cells (up, down, left, right)
            for adj in [(row-1, col), (row+1, col), (row, col-1), (row, col+1)]:
                if adj in cells and adj not in visited:
                    to_visit.add(adj)
        
        return len(visited) == len(cells)
    
    def validate_region_placement(self, region_num, cells):
        # Check for tiles
        for row, col in cells:
            if self.grid_data[row][col].tile:
                return False, "Region cannot cross tile boundaries"
        
        # Check contiguity
        if not self.is_contiguous(cells):
            return False, "Region must be contiguous (all cells must be connected)"
        
        # Check for uniqueness in rows and columns
        rows = {cell[0] for cell in cells}
        cols = {cell[1] for cell in cells}
        
        for row in rows:
            for col in range(self.grid_size):
                cell = self.grid_data[row][col]
                if (row, col) not in cells and cell.region == region_num:
                    return False, "Region number must be unique in each row"
                    
        for col in cols:
            for row in range(self.grid_size):
                cell = self.grid_data[row][col]
                if (row, col) not in cells and cell.region == region_num:
                    return False, "Region number must be unique in each column"
        
        return True, ""
    
    def get_region_color(self, region_num):
        if region_num not in self.region_colors:
            # Generate a light pastel color
            hue = random.random()
            self.region_colors[region_num] = f'#{int(hue * 255):02x}e0e0'
        return self.region_colors[region_num]
    
    def calculate_total_sum(self):
        """Calculate the total sum of all digits in the grid"""
        total = 0
        for row in range(self.grid_size):
            for col in range(self.grid_size):
                cell = self.grid_data[row][col]
                if cell.value and cell.value.isdigit():
                    total += int(cell.value)
        return total

    def update_total_sum(self):
        """Update the total sum display"""
        total = self.calculate_total_sum()
        self.total_sum_var.set(f"Total Sum: {total}")

    def draw_grid(self):
        self.canvas.delete('all')
        
        # Draw cells first
        for row in range(self.grid_size):
            for col in range(self.grid_size):
                # Add padding to all coordinates
                x1 = col * self.cell_size + self.grid_padding
                y1 = row * self.cell_size + self.grid_padding
                x2 = x1 + self.cell_size
                y2 = y1 + self.cell_size
                
                cell = self.grid_data[row][col]
                
                # Draw base white background for all cells
                self.canvas.create_rectangle(x1, y1, x2, y2, fill='white', outline='')
                
                # Draw selection overlay if cell is selected
                if (row, col) in self.selected_cells:
                    self.canvas.create_rectangle(x1, y1, x2, y2, fill='#e0e8ff', outline='')
                
                # Draw yellow background for yellow cells
                if cell.yellow:
                    self.canvas.create_rectangle(x1, y1, x2, y2, fill='yellow', outline='')
                
                # Draw black tiles last
                if cell.tile:
                    self.canvas.create_rectangle(x1, y1, x2, y2, fill='black', outline='')
                    # Show original value (displaced value) in white text
                    if cell.original_value:
                        # Calculate used increments for this tile
                        used_increments = 0
                        for r in range(self.grid_size):
                            for c in range(self.grid_size):
                                adj_cell = self.grid_data[r][c]
                                if (row, col) in adj_cell.contributing_tiles:
                                    current_value = int(adj_cell.value) if adj_cell.value else 0
                                    orig_value = int(adj_cell.original_value) if adj_cell.original_value else 0
                                    used_increments += (current_value - orig_value)
                        
                        remaining = int(cell.original_value) - used_increments
                        if remaining > 0:
                            self.canvas.create_text((x1 + x2) / 2, (y1 + y2) / 2,
                                                text=f"{remaining}",
                                                font=('Arial', 12, 'bold'),
                                                fill='white')
                else:
                    # Draw value (only in solve mode)
                    if not self.editor_mode and cell.value:
                        # Determine if cell has been incremented
                        is_incremented = bool(cell.contributing_tiles)
                        
                        # Center the value in the cell
                        self.canvas.create_text((x1 + x2) / 2, (y1 + y2) / 2,
                                            text=str(cell.value),
                                            font=('Arial', 16, 'bold'),
                                            fill='red' if is_incremented else 'blue')
        
        # Draw all grid lines first (thin lines)
        for i in range(self.grid_size + 1):
            # Vertical lines
            x = i * self.cell_size + self.grid_padding
            self.canvas.create_line(
                x, self.grid_padding,
                x, self.grid_size * self.cell_size + self.grid_padding,
                fill='#e0e0e0', width=1
            )
            # Horizontal lines
            y = i * self.cell_size + self.grid_padding
            self.canvas.create_line(
                self.grid_padding, y,
                self.grid_size * self.cell_size + self.grid_padding, y,
                fill='#e0e0e0', width=1
            )
        
        # Draw region borders on top
        for row in range(self.grid_size):
            for col in range(self.grid_size):
                x1 = col * self.cell_size + self.grid_padding
                y1 = row * self.cell_size + self.grid_padding
                x2 = x1 + self.cell_size
                y2 = y1 + self.cell_size
                
                cell = self.grid_data[row][col]
                
                if cell.region is not None:
                    # Top edge
                    if row == 0 or self.grid_data[row-1][col].region != cell.region:
                        self.canvas.create_line(x1, y1, x2, y1, fill='black', width=2)
                    
                    # Bottom edge
                    if row == self.grid_size-1 or self.grid_data[row+1][col].region != cell.region:
                        self.canvas.create_line(x1, y2, x2, y2, fill='black', width=2)
                    
                    # Left edge
                    if col == 0 or self.grid_data[row][col-1].region != cell.region:
                        self.canvas.create_line(x1, y1, x1, y2, fill='black', width=2)
                    
                    # Right edge
                    if col == self.grid_size-1 or self.grid_data[row][col+1].region != cell.region:
                        self.canvas.create_line(x2, y1, x2, y2, fill='black', width=2)
        
        # Draw outer grid border last
        self.canvas.create_rectangle(
            self.grid_padding, self.grid_padding,
            self.grid_size * self.cell_size + self.grid_padding,
            self.grid_size * self.cell_size + self.grid_padding,
            outline='black', width=2
        )
        
        # If in tile placement mode, show increment buttons
        if self.placing_tile:
            self.show_increment_buttons()
            
        # Update the total sum display
        self.update_total_sum()
    
    def on_mouse_down(self, event):
        coords = self.get_cell_coords(event)
        if not coords:
            if self.placing_tile:
                self.cleanup_tile_placement()
                self.draw_grid()
            return
            
        row, col = coords
        
        # If we're in solve mode and currently placing/redistributing a tile
        if not self.editor_mode and self.placing_tile:
            # If clicked on a cell that's not adjacent to the current tile
            if coords not in self.get_adjacent_cells(*self.tile_position) and coords != self.tile_position:
                self.cleanup_tile_placement()
                self.draw_grid()
                
                # If clicked on a different tile, start new redistribution
                if self.grid_data[row][col].tile:
                    self.start_redistribution(row, col)
                return
            return
            
        # If we're in solve mode and click a tile to start redistribution
        if not self.editor_mode and self.grid_data[row][col].tile:
            # Only start redistribution if the tile has remaining increments to distribute
            self.start_redistribution(row, col)
        
        # Always allow selection, even for tiles
        self.selection_start = coords
        self.selected_cells = {coords}
        if self.editor_mode:
            self.current_region_input = ""  # Reset region input
        self.draw_grid()
    
    def on_mouse_drag(self, event):
        if not self.selection_start:
            return
            
        # In solve mode, only allow single cell selection
        if not self.editor_mode:
            return
            
        end_coords = self.get_cell_coords(event)
        if end_coords:
            # Get all cells in the rectangle
            start_row, start_col = self.selection_start
            end_row, end_col = end_coords
            
            min_row, max_row = min(start_row, end_row), max(start_row, end_row)
            min_col, max_col = min(start_col, end_col), max(start_col, end_col)
            
            # Create new selection set
            new_selection = set()
            for row in range(min_row, max_row + 1):
                for col in range(min_col, max_col + 1):
                    if 0 <= row < self.grid_size and 0 <= col < self.grid_size:
                        new_selection.add((row, col))
            
            self.selected_cells = new_selection
            self.draw_grid()
    
    def on_mouse_up(self, event):
        self.selection_start = None
    
    def on_shift_click(self, event):
        if not self.editor_mode:
            return
            
        coords = self.get_cell_coords(event)
        if coords:
            if coords in self.selected_cells:
                self.selected_cells.remove(coords)
            else:
                self.selected_cells.add(coords)
            self.draw_grid()
    
    def process_region_input(self):
        if self.selected_cells and self.current_region_input:
            if self.current_region_input.isdigit():
                region_num = int(self.current_region_input)
                if 1 <= region_num <= 99:
                    valid, message = self.validate_region_placement(region_num, self.selected_cells)
                    if valid:
                        for row, col in self.selected_cells:
                            cell = self.grid_data[row][col]
                            if not cell.tile:
                                cell.region = region_num
                    else:
                        messagebox.showerror("Invalid Region", message)
        
        self.current_region_input = ""
        self.draw_grid()
    
    def get_cells_in_region(self, region_num):
        cells = []
        for row in range(self.grid_size):
            for col in range(self.grid_size):
                if self.grid_data[row][col].region == region_num:
                    cells.append((row, col))
        return cells

    def get_orthogonal_neighbors(self, row, col):
        """Get orthogonally adjacent cells (up, down, left, right)"""
        neighbors = []
        for r, c in [(row-1, col), (row+1, col), (row, col-1), (row, col+1)]:
            if 0 <= r < self.grid_size and 0 <= c < self.grid_size:
                neighbors.append((r, c))
        return neighbors
    
    def is_valid_number_placement(self, row, col, value, ignore_region=None):
        """Check if a number can be placed in a cell according to the rules"""
        cell = self.grid_data[row][col]
        
        # Get all orthogonally adjacent cells
        neighbors = self.get_orthogonal_neighbors(row, col)
        
        # Check each neighbor
        for n_row, n_col in neighbors:
            neighbor = self.grid_data[n_row][n_col]
            
            # Skip if neighbor is in the same region or is the region we're ignoring
            if neighbor.region == cell.region or neighbor.region == ignore_region:
                continue
                
            # Skip if neighbor has no value
            if not neighbor.value:
                continue
                
            # If neighbor is in a different region and has the same value, it's invalid
            if neighbor.value == str(value):
                return False
        
        return True
    
    def on_key(self, event):
        # Early return only if no cells are selected
        if not self.selected_cells:
            return
            
        if self.editor_mode:
            # Editor mode logic
            if event.char.isdigit():
                self.current_region_input += event.char
                if len(self.current_region_input) >= 2:
                    self.process_region_input()
                else:
                    if self.region_input_timer:
                        self.root.after_cancel(self.region_input_timer)
                    self.region_input_timer = self.root.after(500, self.process_region_input)
            
            elif event.char == 'y':
                for row, col in self.selected_cells:
                    cell = self.grid_data[row][col]
                    cell.yellow = not cell.yellow
            
            elif event.char == 'r':
                # Get all unique regions in the selection
                regions_to_remove = set()
                for row, col in self.selected_cells:
                    cell = self.grid_data[row][col]
                    if cell.region is not None:
                        regions_to_remove.add(cell.region)
                
                # Remove each region
                for region_num in regions_to_remove:
                    self.remove_region(region_num)
        
        else:  # Solve mode
            if event.char.isdigit() and '1' <= event.char <= '9':
                # Get the first selected cell to check its region
                first_cell_coords = next(iter(self.selected_cells))
                first_cell = self.grid_data[first_cell_coords[0]][first_cell_coords[1]]
                
                # If the cell is part of a region, validate and update all cells in that region
                if first_cell.region is not None:
                    region_cells = self.get_cells_in_region(first_cell.region)
                    
                    # First check if the number can be placed in all cells of the region
                    valid_placement = True
                    for row, col in region_cells:
                        if not self.is_valid_number_placement(row, col, event.char):
                            valid_placement = False
                            break
                    
                    if not valid_placement:
                        messagebox.showwarning("Invalid Move", 
                            "This number would create adjacent cells with the same value in different regions.")
                        return
                    
                    # If valid, update all cells in the region
                    for row, col in region_cells:
                        cell = self.grid_data[row][col]
                        # If the cell has a tile, remove it first
                        if cell.tile:
                            self.remove_tile(row, col)
                        cell.value = event.char
                else:
                    # If not part of a region, validate and update just the selected cell
                    for row, col in self.selected_cells:
                        if not self.is_valid_number_placement(row, col, event.char):
                            messagebox.showwarning("Invalid Move", 
                                "This number would create adjacent cells with the same value in different regions.")
                            return
                        
                        cell = self.grid_data[row][col]
                        # If the cell has a tile, remove it first
                        if cell.tile:
                            self.remove_tile(row, col)
                        cell.value = event.char
            
            elif event.char == 't':  # Toggle tile in solve mode
                # Only allow single cell selection for tile placement
                if len(self.selected_cells) == 1:
                    row, col = next(iter(self.selected_cells))
                    cell = self.grid_data[row][col]
                    
                    if cell.tile:
                        # Always allow removal of tiles
                        self.remove_tile(row, col)
                    else:
                        self.place_tile(row, col)
                else:
                    messagebox.showwarning("Invalid Selection",
                                         "Please select exactly one cell to place/remove a tile")
        
        # Always redraw the grid after any changes
        self.draw_grid()
        # Force an immediate update of the canvas
        self.canvas.update()
    
    def on_enter(self, event):
        if self.editor_mode and self.current_region_input:
            self.process_region_input()
    
    def on_backspace(self, event):
        if not self.selected_cells:
            return
            
        # Get all unique regions in the selection
        regions_to_remove = set()
        for row, col in self.selected_cells:
            cell = self.grid_data[row][col]
            if self.editor_mode:
                if cell.region is not None:
                    regions_to_remove.add(cell.region)
                cell.yellow = False
                cell.value = ""
                # Remove tile if present
                if cell.tile:
                    self.remove_tile(row, col)
            else:  # Solve mode
                # If the cell is part of a region, clear all cells in that region
                if cell.region is not None:
                    region_cells = self.get_cells_in_region(cell.region)
                    for r, c in region_cells:
                        # Remove any tiles first
                        if self.grid_data[r][c].tile:
                            self.remove_tile(r, c)
                        self.grid_data[r][c].value = ""
                else:
                    # Remove any tiles first
                    if cell.tile:
                        self.remove_tile(row, col)
                    cell.value = ""
        
        # Remove any regions found
        for region_num in regions_to_remove:
            self.remove_region(region_num)
        
        self.draw_grid()

    def get_adjacent_cells(self, row, col):
        """Get valid adjacent cells (non-yellow, non-tile)"""
        adjacent = []
        for r, c in [(row-1, col), (row+1, col), (row, col-1), (row, col+1)]:
            if (0 <= r < self.grid_size and 0 <= c < self.grid_size and
                not self.grid_data[r][c].yellow and
                not self.grid_data[r][c].tile):
                adjacent.append((r, c))
        return adjacent
    
    def has_adjacent_tiles(self, row, col):
        """Check if any adjacent cell has a tile"""
        for r, c in [(row-1, col), (row+1, col), (row, col-1), (row, col+1)]:
            if (0 <= r < self.grid_size and 0 <= c < self.grid_size and
                self.grid_data[r][c].tile):
                return True
        return False
    
    def can_place_tile(self, row, col):
        """Check if a tile can be placed at the given position"""
        cell = self.grid_data[row][col]
        
        # Check basic conditions
        if (cell.yellow or cell.tile or
            cell.region is None or
            not cell.value or
            not cell.value.isdigit() or
            int(cell.value) < 1 or
            int(cell.value) > 9 or
            self.has_adjacent_tiles(row, col)):
            return False
            
        # Check if increments would exceed 9 in any adjacent cell
        adjacent_cells = self.get_adjacent_cells(row, col)
        if not adjacent_cells:  # Must have at least one valid adjacent cell
            return False
            
        return True
    
    def place_tile(self, row, col):
        """Start tile placement process"""
        if not self.can_place_tile(row, col):
            return False
            
        cell = self.grid_data[row][col]
        self.displaced_value = int(cell.value)
        self.remaining_increments = self.displaced_value
        self.placing_tile = True
        self.tile_position = (row, col)
        
        # Place the tile immediately
        cell.tile = True
        cell.original_value = cell.value
        cell.value = ""
        
        # Show increment buttons
        self.show_increment_buttons()
        self.draw_grid()
        return True
    
    def show_increment_buttons(self):
        """Show increment buttons around the placed tile"""
        # Clear any existing buttons
        for btn in self.increment_buttons:
            btn.destroy()
        self.increment_buttons.clear()
        
        if not self.tile_position:
            return
            
        row, col = self.tile_position
        adjacent_cells = self.get_adjacent_cells(row, col)
        
        # Create a custom style for small buttons
        style = ttk.Style()
        style.configure('Small.TButton', padding=0)
        
        # Button dimensions
        button_width = 18  # Width of the button in pixels
        
        for adj_row, adj_col in adjacent_cells:
            adj_cell = self.grid_data[adj_row][adj_col]
            
            # Skip cells without valid numbers
            if not adj_cell.value or not adj_cell.value.isdigit():
                continue
                
            current_increments = 0
            
            # Calculate current increments from this tile
            if self.tile_position in adj_cell.contributing_tiles:
                base_value = int(adj_cell.original_value) if adj_cell.original_value else 0
                current_value = int(adj_cell.value)
                # Calculate increments only from this tile
                other_tiles_increments = sum(1 for tile in adj_cell.contributing_tiles if tile != self.tile_position)
                current_increments = current_value - base_value - other_tiles_increments
            
            # Calculate button positions
            x_base = adj_col * self.cell_size + self.grid_padding
            y_base = adj_row * self.cell_size + self.grid_padding
            cell_right_edge = x_base + self.cell_size
            
            # Add + button if we have remaining increments and current value is less than 9
            if self.remaining_increments > 0 and int(adj_cell.value) < 9:
                plus_btn = ttk.Button(self.canvas, 
                                  text="+",
                                  style='Small.TButton',
                                  width=1,
                                  command=lambda r=adj_row, c=adj_col: self.increment_adjacent(r, c))
                plus_btn.place(x=x_base + 1, y=y_base + 1)
                self.increment_buttons.append(plus_btn)
            
            # Add - button if the cell has increments from this tile
            if current_increments > 0:
                minus_btn = ttk.Button(self.canvas, 
                                   text="-",
                                   style='Small.TButton',
                                   width=1,
                                   command=lambda r=adj_row, c=adj_col: self.decrement_adjacent(r, c))
                minus_btn.place(x=cell_right_edge - button_width - 1, y=y_base + 1)
                self.increment_buttons.append(minus_btn)
    
    def increment_adjacent(self, row, col):
        """Handle increment button click"""
        if self.remaining_increments <= 0:
            return
            
        cell = self.grid_data[row][col]
        
        # Don't allow incrementing cells without a valid number
        if not cell.value or not cell.value.isdigit():
            messagebox.showwarning("Invalid Increment",
                                 "Cannot increment a cell without a valid number")
            return
            
        current_value = int(cell.value)
        
        if current_value >= 9:
            messagebox.showwarning("Invalid Increment",
                                 "Cannot increment above 9")
            return
            
        # Store original value if not already stored
        if not cell.original_value:
            cell.original_value = cell.value
            
        # Increment the cell
        new_value = current_value + 1
        cell.value = str(new_value)
        cell.increment_value += 1
        cell.contributing_tiles.add(self.tile_position)
        
        # Update remaining increments
        self.remaining_increments -= 1
        
        # If all increments are used, finish tile placement
        if self.remaining_increments == 0:
            self.finish_tile_placement()
        
        self.draw_grid()
    
    def decrement_adjacent(self, row, col):
        """Remove one increment from an adjacent cell"""
        if not self.placing_tile:
            return
            
        cell = self.grid_data[row][col]
        if not cell.value or self.tile_position not in cell.contributing_tiles:
            return
            
        current_value = int(cell.value)
        base_value = int(cell.original_value) if cell.original_value else 0
        
        # Calculate increments only from this tile
        other_tiles_increments = sum(1 for tile in cell.contributing_tiles if tile != self.tile_position)
        current_increments = current_value - base_value - other_tiles_increments
        
        if current_increments <= 0:
            return
            
        # Remove one increment
        new_value = current_value - 1
        cell.value = str(new_value)
        
        # Update remaining increments
        self.remaining_increments += 1
        
        # If this was the last increment from this tile, remove it from contributing_tiles
        if current_increments == 1:
            cell.contributing_tiles.remove(self.tile_position)
            # If no more contributing tiles, restore original value
            if not cell.contributing_tiles:
                cell.value = cell.original_value
                cell.original_value = ""
                cell.increment_value = 0
        
        self.show_increment_buttons()
        self.draw_grid()
    
    def cancel_tile_placement(self):
        """Cancel tile placement and revert changes"""
        if self.tile_position:
            row, col = self.tile_position
            cell = self.grid_data[row][col]
            cell.tile = False
            cell.value = cell.original_value
            cell.original_value = ""
            
            # Revert any increments made
            for r in range(self.grid_size):
                for c in range(self.grid_size):
                    adj_cell = self.grid_data[r][c]
                    if self.tile_position in adj_cell.contributing_tiles:
                        adj_cell.contributing_tiles.remove(self.tile_position)
                        if not adj_cell.contributing_tiles:
                            adj_cell.value = adj_cell.original_value
                            adj_cell.original_value = ""
                            adj_cell.increment_value = 0
        
        self.cleanup_tile_placement()
        self.draw_grid()
    
    def finish_tile_placement(self):
        """Complete tile placement after all increments are used"""
        self.cleanup_tile_placement()
        self.draw_grid()
    
    def cleanup_tile_placement(self):
        """Clean up after tile placement"""
        # Remove increment buttons
        for btn in self.increment_buttons:
            btn.destroy()
        self.increment_buttons.clear()
        
        # Reset tile placement state
        self.placing_tile = False
        self.tile_position = None
        self.displaced_value = 0
        self.remaining_increments = 0
    
    def remove_tile(self, row, col):
        """Remove a tile and revert displacement effects"""
        cell = self.grid_data[row][col]
        if not cell.tile:
            return False
            
        # Get all cells affected by this tile
        for r in range(self.grid_size):
            for c in range(self.grid_size):
                adj_cell = self.grid_data[r][c]
                if (row, col) in adj_cell.contributing_tiles:
                    # Remove this tile's contribution
                    current_value = int(adj_cell.value)
                    adj_cell.contributing_tiles.remove((row, col))
                    
                    # If no more contributing tiles, restore original value
                    if not adj_cell.contributing_tiles:
                        adj_cell.value = adj_cell.original_value
                        adj_cell.original_value = ""
                        adj_cell.increment_value = 0
        
        # Restore the tile cell
        cell.tile = False
        cell.value = cell.original_value
        cell.original_value = ""
        
        # Clean up any ongoing tile placement
        self.cleanup_tile_placement()
        
        self.draw_grid()
        return True

    def remove_region(self, region_num):
        """Remove a region and any tiles within it"""
        # First, get all cells in the region
        region_cells = []
        for row in range(self.grid_size):
            for col in range(self.grid_size):
                if self.grid_data[row][col].region == region_num:
                    region_cells.append((row, col))
        
        # First pass: Remove all tiles and their contributions
        for row, col in region_cells:
            cell = self.grid_data[row][col]
            if cell.tile:
                self.remove_tile(row, col)
        
        # Second pass: Reset all cells in the region completely
        for row, col in region_cells:
            cell = self.grid_data[row][col]
            # Reset all cell properties
            cell.value = ""
            cell.region = None
            cell.tile = False
            cell.yellow = False
            cell.original_value = ""
            cell.increment_value = 0
            cell.contributing_tiles = set()
        
        # Third pass: Clean up any remaining increment contributions to/from these cells
        for r in range(self.grid_size):
            for c in range(self.grid_size):
                cell = self.grid_data[r][c]
                # Remove any contributions from cells that were in this region
                for row, col in region_cells:
                    if (row, col) in cell.contributing_tiles:
                        cell.contributing_tiles.remove((row, col))
                        if not cell.contributing_tiles:
                            cell.value = cell.original_value
                            cell.original_value = ""
                            cell.increment_value = 0
                
                # If this cell was contributing to any cells in the region, remove those contributions
                if any((row, col) in region_cells for row, col in cell.contributing_tiles):
                    cell.contributing_tiles = {pos for pos in cell.contributing_tiles 
                                            if pos not in region_cells}
                    if not cell.contributing_tiles:
                        cell.value = cell.original_value
                        cell.original_value = ""
                        cell.increment_value = 0
        
        # Clean up any ongoing tile placement
        self.cleanup_tile_placement()

    def save_layout(self):
        try:
            filename = "puzzle_layout.csv"
            with open(filename, 'w', newline='') as f:
                writer = csv.writer(f)
                # Write header - remove tile-related columns
                writer.writerow(['Row', 'Col', 'Value', 'Region', 'Yellow'])
                # Write cell data
                for row in range(self.grid_size):
                    for col in range(self.grid_size):
                        cell = self.grid_data[row][col]
                        # Convert region None to empty string for CSV
                        region_str = "" if cell.region is None else str(cell.region)
                        # Only save basic cell data, no tile information
                        cell_data = [
                            row,
                            col,
                            cell.value,
                            region_str,
                            "1" if cell.yellow else "0"
                        ]
                        writer.writerow(cell_data)
            messagebox.showinfo("Success", f"Layout saved to {filename}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save layout: {str(e)}")

    def load_layout(self):
        try:
            filename = "puzzle_layout.csv"
            if not os.path.exists(filename):
                messagebox.showwarning("Warning", "No saved layout found.")
                return
                
            with open(filename, 'r', newline='') as f:
                reader = csv.reader(f)
                header = next(reader)  # Read header row
                
                # Reset grid to empty state
                self.grid_data = [[GridCell() for _ in range(self.grid_size)] 
                                for _ in range(self.grid_size)]
                
                # Load cell data
                for row in reader:
                    if len(row) >= 4:  # Minimum required columns
                        r, c = int(row[0]), int(row[1])
                        if 0 <= r < self.grid_size and 0 <= c < self.grid_size:
                            cell = self.grid_data[r][c]
                            
                            # Load only basic cell data
                            cell.value = row[2]
                            cell.region = None if row[3] == "" else int(row[3])
                            cell.yellow = row[4] == "1" if len(row) > 4 else False
                            
                            # Ensure tile-related properties are reset
                            cell.tile = False
                            cell.original_value = ""
                            cell.increment_value = 0
                            cell.contributing_tiles = set()
                
                self.selected_cells.clear()
                self.draw_grid()
                messagebox.showinfo("Success", "Layout loaded successfully!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load layout: {str(e)}")

    def start_redistribution(self, row, col):
        """Start redistributing increments from a tile"""
        cell = self.grid_data[row][col]
        if not cell.tile or not cell.original_value:
            return False
            
        # Calculate used increments and track which cells have increments
        used_increments = 0
        has_distributed_increments = False
        for r in range(self.grid_size):
            for c in range(self.grid_size):
                adj_cell = self.grid_data[r][c]
                if (row, col) in adj_cell.contributing_tiles:
                    has_distributed_increments = True
                    current_value = int(adj_cell.value) if adj_cell.value else 0
                    orig_value = int(adj_cell.original_value) if adj_cell.original_value else 0
                    used_increments += (current_value - orig_value)
        
        # Allow editing if there are remaining increments OR if the tile has distributed any increments
        if used_increments < int(cell.original_value) or has_distributed_increments:
            self.displaced_value = int(cell.original_value)
            self.remaining_increments = int(cell.original_value) - used_increments
            self.placing_tile = True
            self.tile_position = (row, col)
            self.show_increment_buttons()
            self.draw_grid()
            return True
        return False

def main():
    root = tk.Tk()
    app = LogicPuzzleGrid(root)
    root.mainloop()

if __name__ == "__main__":
    main()
