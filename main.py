import os
from PyPDF2 import PdfReader, PdfWriter
import tkinter as tk
from tkinter import filedialog, ttk, messagebox
import fitz  # PyMuPDF
from PIL import Image, ImageTk
import io
import re
import sys

class PDFExtractorApp:
    """
    A GUI application for extracting pages from PDF files.
    
    This application allows users to:
    - Load PDF files and preview their pages
    - Select individual pages or page ranges
    - Extract selected pages to a new PDF file
    """
    def __init__(self, root):
        self.root = root
        self.root.title("PDF Page Extractor")
        self.root.geometry("1000x700")
        
        # Set application icon if available
        try:
            if os.path.exists("icon.ico"):
                self.root.iconbitmap("icon.ico")
        except:
            pass
        
        self.input_pdf_path = ""
        self.output_pdf_path = ""
        self.current_page = 0
        self.total_pages = 0
        self.pdf_document = None
        self.selected_pages = set()
        self.zoom_level = 1.5  # Default zoom level
        
        self.create_widgets()
        
        # Create screenshots directory if it doesn't exist
        os.makedirs("screenshots", exist_ok=True)
        
    def create_widgets(self):
        # Top frame for file selection
        top_frame = ttk.Frame(self.root, padding="10")
        top_frame.pack(fill=tk.X)
        
        ttk.Label(top_frame, text="Input PDF:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.input_entry = ttk.Entry(top_frame, width=50)
        self.input_entry.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W+tk.E)
        ttk.Button(top_frame, text="Browse", command=self.browse_input_file).grid(row=0, column=2, padx=5, pady=5)
        
        ttk.Label(top_frame, text="Output PDF:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.output_entry = ttk.Entry(top_frame, width=50)
        self.output_entry.grid(row=1, column=1, padx=5, pady=5, sticky=tk.W+tk.E)
        ttk.Button(top_frame, text="Browse", command=self.browse_output_file).grid(row=1, column=2, padx=5, pady=5)
        
        # Main content frame with preview and controls
        content_frame = ttk.Frame(self.root, padding="10")
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        # PDF Preview with scrollbar
        preview_frame = ttk.LabelFrame(content_frame, text="PDF Preview", padding="10")
        preview_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create a frame to hold the canvas and scrollbar
        canvas_frame = ttk.Frame(preview_frame)
        canvas_frame.pack(fill=tk.BOTH, expand=True)
        
        # Add vertical scrollbar
        scrollbar = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Create canvas with scrollbar
        self.canvas = tk.Canvas(
            canvas_frame, 
            bg="gray", 
            relief=tk.SUNKEN,
            yscrollcommand=scrollbar.set
        )
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Configure the scrollbar
        scrollbar.config(command=self.canvas.yview)
        
        # Add mouse wheel scrolling
        self.canvas.bind("<MouseWheel>", self._on_mousewheel)  # Windows
        self.canvas.bind("<Button-4>", self._on_mousewheel)    # Linux scroll up
        self.canvas.bind("<Button-5>", self._on_mousewheel)    # Linux scroll down
        
        # Page information label below the preview
        self.page_info_label = ttk.Label(
            preview_frame, 
            text="No PDF loaded", 
            anchor=tk.CENTER,
            font=("", 10)
        )
        self.page_info_label.pack(fill=tk.X, pady=(5, 0))
        
        # Navigation and selection frame
        nav_frame = ttk.Frame(content_frame, padding="10", width=200)
        nav_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=5, pady=5)
        
        # Page navigation
        page_nav_frame = ttk.Frame(nav_frame)
        page_nav_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(page_nav_frame, text="<", command=self.prev_page).pack(side=tk.LEFT)
        self.page_label = ttk.Label(page_nav_frame, text="Page 0 of 0")
        self.page_label.pack(side=tk.LEFT, padx=10)
        ttk.Button(page_nav_frame, text=">", command=self.next_page).pack(side=tk.LEFT)
        
        # Page selection
        selection_frame = ttk.LabelFrame(nav_frame, text="Page Selection", padding="10")
        selection_frame.pack(fill=tk.X, pady=10)
        
        # Add page range input field
        range_frame = ttk.Frame(selection_frame)
        range_frame.pack(fill=tk.X, pady=5)
        ttk.Label(range_frame, text="Page Range:").pack(side=tk.LEFT, anchor=tk.W)
        self.range_entry = ttk.Entry(range_frame, width=15)
        self.range_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        ttk.Button(range_frame, text="Add Range", command=self.add_page_range).pack(side=tk.LEFT)
        
        # Help text for range format
        ttk.Label(selection_frame, text="Format: 1,3,5-7,10-15", font=("", 8)).pack(anchor=tk.W)
        
        ttk.Label(selection_frame, text="Selected Pages:").pack(anchor=tk.W, pady=(10, 0))
        self.selected_pages_text = tk.Text(selection_frame, height=5, width=20)
        self.selected_pages_text.pack(fill=tk.X, pady=5)
        
        button_frame = ttk.Frame(selection_frame)
        button_frame.pack(fill=tk.X, pady=5)
        ttk.Button(button_frame, text="Select Current Page", command=self.select_current_page).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        ttk.Button(button_frame, text="Clear Selection", command=self.clear_selection).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        
        # Export button
        export_frame = ttk.Frame(nav_frame)
        export_frame.pack(fill=tk.X, pady=20)
        ttk.Button(export_frame, text="Extract Selected Pages", command=self.extract_pages).pack(fill=tk.X, pady=5)
        
    def _on_mousewheel(self, event):
        """Handle mouse wheel scrolling"""
        # Determine the delta based on the event type
        if event.num == 4:  # Linux scroll up
            delta = 1
        elif event.num == 5:  # Linux scroll down
            delta = -1
        else:  # Windows and macOS
            delta = event.delta // 120  # Windows uses multiples of 120
            
        # Scroll the canvas (multiply by 30 for smoother scrolling)
        self.canvas.yview_scroll(-delta * 3, "units")
    
    def browse_input_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("PDF files", "*.pdf")])
        if file_path:
            self.input_pdf_path = file_path
            self.input_entry.delete(0, tk.END)
            self.input_entry.insert(0, file_path)
            self.load_pdf()
            
            # Set default output name
            if not self.output_entry.get():
                basename = os.path.basename(file_path)
                name, ext = os.path.splitext(basename)
                self.output_entry.insert(0, f"{name}_extracted.pdf")
    
    def browse_output_file(self):
        file_path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")]
        )
        if file_path:
            self.output_pdf_path = file_path
            self.output_entry.delete(0, tk.END)
            self.output_entry.insert(0, file_path)
    
    def load_pdf(self):
        try:
            # Close any open document
            if self.pdf_document:
                self.pdf_document.close()
                
            # Open the PDF with PyMuPDF for preview
            self.pdf_document = fitz.open(self.input_pdf_path)
            self.total_pages = len(self.pdf_document)
            self.current_page = 0
            
            # Update page display
            self.update_page_display()
            
            # Clear selected pages
            self.selected_pages = set()
            self.update_selected_pages_display()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load PDF: {str(e)}")
    
    def update_page_display(self):
        if not self.pdf_document:
            return
            
        # Update page number label in navigation area
        self.page_label.config(text=f"Page {self.current_page + 1} of {self.total_pages}")
        
        # Update page info label below preview
        self.page_info_label.config(
            text=f"Viewing page {self.current_page + 1} of {self.total_pages} • {self.input_pdf_path}"
        )
        
        # Display current page
        self.display_page(self.current_page)
    
    def display_page(self, page_num):
        if not self.pdf_document or page_num < 0 or page_num >= self.total_pages:
            return
            
        # Get the page
        page = self.pdf_document[page_num]
        
        # Render page to an image (increased resolution for better quality)
        pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5))
        img_data = pix.tobytes("ppm")
        
        # Convert to PhotoImage
        img = Image.open(io.BytesIO(img_data))
        self.tk_image = ImageTk.PhotoImage(image=img)
        
        # Update canvas size and configure scrollregion
        canvas_width = self.canvas.winfo_width()
        img_width = img.width
        img_height = img.height
        
        # Center the image horizontally if canvas is wider than image
        x_position = max(0, (canvas_width - img_width) // 2)
        
        # Clear the canvas and create the image
        self.canvas.delete("all")
        self.canvas.create_image(x_position, 0, anchor=tk.NW, image=self.tk_image)
        
        # Configure the scrollregion to match the image size
        self.canvas.config(scrollregion=(0, 0, max(img_width, canvas_width), img_height))
        
        # Reset the scroll position to the top
        self.canvas.yview_moveto(0)
    
    # Make sure the image stays centered when window is resized
    def on_canvas_configure(self, event):
        if hasattr(self, 'tk_image') and self.tk_image:
            # Get the current canvas width and image width
            canvas_width = event.width
            img_width = self.tk_image.width()
            
            # Center the image horizontally
            x_position = max(0, (canvas_width - img_width) // 2)
            
            # Update the image position
            self.canvas.coords("image", x_position, 0)
    
    def prev_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self.update_page_display()
    
    def next_page(self):
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            self.update_page_display()
    
    def select_current_page(self):
        if not self.pdf_document:
            return
            
        self.selected_pages.add(self.current_page + 1)  # Store 1-based page numbers
        self.update_selected_pages_display()
    
    def clear_selection(self):
        self.selected_pages = set()
        self.update_selected_pages_display()
    
    def update_selected_pages_display(self):
        self.selected_pages_text.delete(1.0, tk.END)
        if not self.selected_pages:
            return
            
        # Convert the set of pages to a compact representation
        pages_list = sorted(self.selected_pages)
        
        # Group consecutive pages for better display
        ranges = []
        start = pages_list[0]
        end = start
        
        for i in range(1, len(pages_list)):
            if pages_list[i] == end + 1:
                end = pages_list[i]
            else:
                if start == end:
                    ranges.append(str(start))
                else:
                    ranges.append(f"{start}-{end}")
                start = end = pages_list[i]
                
        # Add the last range
        if start == end:
            ranges.append(str(start))
        else:
            ranges.append(f"{start}-{end}")
            
        self.selected_pages_text.insert(tk.END, ", ".join(ranges))
    
    def add_page_range(self):
        if not self.pdf_document:
            messagebox.showwarning("Warning", "No PDF loaded")
            return
            
        range_text = self.range_entry.get().strip()
        if not range_text:
            messagebox.showwarning("Warning", "Please enter a page range")
            return
            
        try:
            new_pages = self.parse_page_range(range_text, self.total_pages)
            if not new_pages:
                messagebox.showwarning("Warning", "No valid pages in the specified range")
                return
                
            # Add the new pages to the selected pages set
            self.selected_pages.update(new_pages)
            self.update_selected_pages_display()
            
            # Clear the range entry
            self.range_entry.delete(0, tk.END)
            
        except ValueError as e:
            messagebox.showerror("Error", str(e))
    
    def parse_page_range(self, range_text, total_pages):
        """Parse a page range string and return a set of page numbers.
        
        Examples of valid formats:
        - Single pages: 1,3,5
        - Ranges: 1-5,7-9
        - Mixed: 1,3-5,7,9-11
        """
        result = set()
        
        # Split by comma
        parts = range_text.split(',')
        
        for part in parts:
            part = part.strip()
            if not part:
                continue
                
            # Check if it's a range (contains a hyphen)
            if '-' in part:
                try:
                    start, end = map(int, part.split('-'))
                    if start < 1 or end > total_pages:
                        raise ValueError(f"Page range {start}-{end} is out of bounds (1-{total_pages})")
                    if start > end:
                        raise ValueError(f"Invalid range: {start}-{end}. Start must be less than or equal to end.")
                    result.update(range(start, end + 1))
                except ValueError as e:
                    if "is out of bounds" in str(e) or "Start must be less than" in str(e):
                        raise e
                    raise ValueError(f"Invalid range format: {part}. Use start-end (e.g., 1-5)")
            else:
                # Single page
                try:
                    page = int(part)
                    if page < 1 or page > total_pages:
                        raise ValueError(f"Page {page} is out of bounds (1-{total_pages})")
                    result.add(page)
                except ValueError as e:
                    if "is out of bounds" in str(e):
                        raise e
                    raise ValueError(f"Invalid page number: {part}. Must be a number.")
                    
        return result
    
    def extract_pages(self):
        """Extract selected pages from the PDF and save to a new file."""
        if not self.pdf_document:
            messagebox.showwarning("Warning", "No PDF loaded")
            return
            
        if not self.selected_pages:
            messagebox.showwarning("Warning", "No pages selected")
            return
            
        output_path = self.output_entry.get()
        if not output_path:
            messagebox.showwarning("Warning", "No output path specified")
            return
            
        try:
            reader = PdfReader(self.input_pdf_path)
            writer = PdfWriter()
            
            # Add selected pages to output
            for page_num in sorted(self.selected_pages):
                writer.add_page(reader.pages[page_num - 1])  # Convert to 0-based index
                
            # Create output directory if it doesn't exist
            output_dir = os.path.dirname(output_path)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir)
                
            # Write to file
            with open(output_path, 'wb') as output_file:
                writer.write(output_file)
                
            messagebox.showinfo("Success", f"Successfully extracted {len(self.selected_pages)} pages to {output_path}")
            
            # Ask if user wants to open the new PDF
            if messagebox.askyesno("Open PDF", "Would you like to open the extracted PDF?"):
                self.open_pdf(output_path)
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to extract pages: {str(e)}")

    def open_pdf(self, pdf_path):
        """Open a PDF file with the default PDF viewer."""
        try:
            import subprocess
            import platform
            
            system = platform.system()
            if system == 'Darwin':  # macOS
                subprocess.call(('open', pdf_path))
            elif system == 'Windows':
                os.startfile(pdf_path)
            else:  # Linux
                subprocess.call(('xdg-open', pdf_path))
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open PDF: {str(e)}")
    
    def take_screenshot(self):
        """Save a screenshot of the current PDF page."""
        if not self.pdf_document:
            messagebox.showwarning("Warning", "No PDF loaded")
            return
            
        try:
            # Create screenshots directory if it doesn't exist
            if not os.path.exists("screenshots"):
                os.makedirs("screenshots")
                
            # Get filename without extension
            base_file = os.path.splitext(os.path.basename(self.input_pdf_path))[0]
            output_file = f"screenshots/{base_file}_page{self.current_page + 1}.png"
            
            # Get the page
            page = self.pdf_document[self.current_page]
            
            # Render page to an image with higher resolution
            pix = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0))
            
            # Save the image
            pix.save(output_file)
            
            messagebox.showinfo("Screenshot Saved", f"Screenshot saved as {output_file}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save screenshot: {str(e)}")

def main():
    """Main entry point of the application."""
    root = tk.Tk()
    app = PDFExtractorApp(root)
    
    # Bind configure event to reposition the image when canvas is resized
    app.canvas.bind("<Configure>", app.on_canvas_configure)
    
    # Add right-click menu for screenshot
    if hasattr(app, 'canvas'):
        def show_context_menu(event):
            context_menu = tk.Menu(root, tearoff=0)
            context_menu.add_command(label="Take Screenshot", command=app.take_screenshot)
            context_menu.post(event.x_root, event.y_root)
        
        app.canvas.bind("<Button-3>", show_context_menu)  # Right-click
    
    root.mainloop()

if __name__ == "__main__":
    main()
