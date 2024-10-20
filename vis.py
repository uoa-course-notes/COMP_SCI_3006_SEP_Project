import tkinter as tk
import time

TABLE_SCALE = 5.0 / 6
VERTICAL_SCALE = 9.0 / 10

class Window:
    """
    The main window; this will hold all widgets after leaving the splash screen.

    :param x: x position of splash screen; this helps ensure the window is in the same place as the splash screen
    :param y: y position of the splash screen

        """
    def __init__(self, x, y):
        
        self.vertical_space = 50
        self.horizontal_space = 100

        self.crossids = set()
        self.upids = set()
        self.mode = "insert"
        self.step = False

        self.ghost_ray = None
        self.ghost_dot = None

        self.linedotid = {}

        self.line_quantized_coords = {}
        self.dot_quantized_coords = {}

        # no lines allowed on same coordinates
        self.taken_x = set()
        self.taken_y = set()

        self.last_toggle = 0
        self.query_id = None
        self.window = tk.Tk()

        self.window.geometry("600x300+%d+%d" % (x, y))
        self.window.minsize(600, 300)
        self.window.wm_title("rpqvis")
        self.canvas = tk.Canvas(self.window, width=600, height=300)
        self.canvas.bind("<Button-1>", self.clicked)
        self.window.bind("<d>", self.toggle)
        self.window.bind("<i>", self.toggle)
        self.window.bind("<q>", self.toggle)
        self.window.bind("<s>", self.toggle)
        self.canvas.bind("<Configure>", self.resize)
        self.canvas.pack()

        self.help_btn = tk.Button(self.canvas, text="Help", command=self.popup)
        self.mode_label = self.canvas.create_text(515, 15, font="14", anchor="nw", text="Mode:")
        self.delete_btn = tk.Radiobutton(self.canvas, text="Delete", command=self.toggle_delete, variable=self.mode, value="delete")
        self.insert_btn = tk.Radiobutton(self.canvas, text="Insert", command=self.toggle_insert, variable=self.mode, value="insert")
        self.query_btn = tk.Radiobutton(self.canvas, text="Query", command=self.toggle_query, variable=self.mode, value="query")
        
        self.delete_btn.deselect()
        self.query_btn.deselect()
        self.insert_btn.select()

        self.bottom_rect = self.canvas.create_rectangle(0, 270, 500, 300, fill="black")
        self.table_sep = self.canvas.create_line(500, 0, 500, 300, fill="black")
        self.table_label = self.canvas.create_text(515, 145, font="14", anchor="nw",
            text="Elements \nat t=∞:")
        self.table_text = self.canvas.create_text(520, 185, font="12", anchor="nw", text="")
        
        self.pairs = dict()

        self.canvas.bind('<Motion>', self.motion)
        self.last_highlight = -1
        self.w = 600
        self.h = 300
        self.step_btn = tk.Button(self.canvas, text="Step", command=self.toggle_step)

        self.help_btn.place(x=520, y=270, width=70)
        self.insert_btn.place(x=520, y=35, width=70)
        self.delete_btn.place(x=520, y=60, width=70)
        self.query_btn.place(x=520, y=85, width=70)
        self.step_btn.place(x=520, y=110, width=60)
        self.canvas.addtag_all("all")

        self.window.mainloop()

    def popup(self):
        """
        Open the help popup.
        """

        inst = "rpqvis is a visualization of retroactive priority queues. In Insert mode, you can insert \"insert\" operations by pressing on the white part of the screen and insert \"delete-min\" operations by pressing in the bottom black bar.  In Delete mode you can delete those operations by hovering over lines and clicking. In Query mode you can query what is in the priority queue at any time in history. If step-through (Step) is enabled, propagation of operations is slowed down so you can see changes happening.\n\nDocumentation of the source code can be found at https://6851-2021.github.io/rpqvis/".split()


        x = self.window.winfo_x()+self.window.winfo_width()/2-200
        y = self.window.winfo_y()+self.window.winfo_height()/2-115
        


        popup = tk.Tk()
        popup.geometry("400x230+%d+%d"% (x, y))
        popup.wm_title("Help")
        popup.minsize(400, 230)
        popup.maxsize(400, 230)

        new_inst = ""
        linelen = 0

        # wrap by word
        for word in inst:
            if linelen+len(word)+1> 400/7:
                new_inst+="\n"
                linelen = 0
            linelen+= len(word)+1
            new_inst += " " + word


        label = tk.Label(popup, text=new_inst)
        label.pack(side="top", fill="x", pady=10)
        button = tk.Button(popup, text="Okay", command = popup.destroy)
        button.pack()
        popup.mainloop()

    def quantize(self, t, y, w, h):
        """
        Map actual location onto a lattice; return the nearest lattice point.

        :param t: actual t coordinate
        :param y: actual y coordinate
        :param w: width of window
        :param h: height of window
        """
        qt = round(t/(w*TABLE_SCALE)*self.horizontal_space)
        qy = round(y/h*self.vertical_space)
        return qt, qy

    def quantize_line(self, c, w, h):
        """
        Helper function; map line endpoints onto a lattice.

        :param c: actual line coordinates
        :param w: width of window
        :param h: height of window
        """
        pt1 = self.quantize(c[0], c[1], w, h)
        pt2 = self.quantize(c[2], c[3], w, h)
        return (pt1[0], pt1[1], pt2[0], pt2[1])

    def unquantize(self, qt, qy, w, h):
        """
        Map lattice point to actual location.

        :param qt: "quantized" t coordinate
        :param qy: "quantized" y coordinate
        :param w: width of window
        :param h: height of window
        """
        t = round(qt/self.horizontal_space*(w*TABLE_SCALE))
        y = round(qy/self.vertical_space*h)
        return t, y

    def display_table(self, t=99):
        """
        Set table text to result of query at time t.

        :param t: time of query
        """
        self.canvas.itemconfig(self.table_text, text=
            '\n'.join([str(round(9/10*self.vertical_space-l)) for l in self.query(t)]))

    def display_line(self, qt1, qy1, qt2, qy2, fill="black"):
        """
        Display a line, given "quantized" endpoint coordinates.

        :param qt1: "quantized" t coordinate of first endpoint
        :param qy1: "quantized" y coordinate of first endpoint
        :param qt2: "quantized" t coordinate of second endpoint
        :param qy2: "quantized" y coordinate of second endpoint
        :param fill: color of line
        """
        t1, y1 = self.unquantize(qt1, qy1, self.w, self.h)
        t2, y2 = self.unquantize(qt2, qy2, self.w, self.h)

        id = self.canvas.create_line(t1, y1, t2, y2, arrow=tk.LAST, fill=fill)
        return id

    def display_dot(self, qt, qy, fill="black", outline="black"):
        """
        Display a dot, given "quantized" coordinates.

        :param qt: "quantized" t coordinate
        :param qy: "quantized" y coordinate
        :param fill: color of dot
        :param outline: color of outline of dot
        """
        t, y = self.unquantize(qt, qy, self.w, self.h)
        id = self.canvas.create_oval(t-3, y-3, t+3, y+3, fill=fill, outline=outline)
        return id

    def scale_line(self, id):
        """
        Resize and shift an existing line, based on lattice coordinates.

        :param id: tkinter ID number of line
        """
        c = self.line_quantized_coords[id]
        pt1 = self.unquantize(c[0], c[1], self.w, self.h)
        pt2 = self.unquantize(c[2], c[3], self.w, self.h)

        self.canvas.coords(id, pt1[0], pt1[1], pt2[0], pt2[1])

    def scale_dot(self, id):
        """
        Shift an existing dot, based on lattice coordinates.

        :param id: tkinter ID number of dot
        """
        c = self.dot_quantized_coords[id]
        pt1 = self.unquantize(c[0], c[1], self.w, self.h)
        self.canvas.coords(id, pt1[0]+3, pt1[1]+3, pt1[0]-3, pt1[1]-3)

    def query(self, t):
        """
        Return items in the priority queue at time t.

        :param t: time of query
        """
        existlist = []
        for line in self.crossids:
            c = self.line_quantized_coords[line]
            if c[2] > t and c[0] <= t:
                existlist.append(c[1])

        return sorted(existlist, reverse=False)

    def resize(self, event):  
        """
        Shift and resize on-screen graphics if the window is resized.

        :param event: tkinter event, holding new width and height
        """      
        rw = float(event.width)/self.w
        rh = float(event.height)/self.h

        # resize the canvas 
        self.canvas.config(width=event.width, height=event.height)
        # rescale all the objects tagged with the "all" tag
        self.canvas.scale("all", 0, 0, rw, rh)

        self.canvas.scale(self.table_label, 0, 0, 1.0, 1/rh)
        self.canvas.scale(self.table_text, 0, 0, 1.0, 1/rh)

        self.w = event.width
        self.h = event.height

        for line in self.crossids:
            self.scale_line(line)

        for line in self.upids:
            self.scale_line(line)

        for k in self.linedotid:
            dot = self.linedotid[k]
            self.scale_dot(dot)

        button_x = event.width*TABLE_SCALE + (event.width - event.width*TABLE_SCALE)*.5 - 30
        self.help_btn.place(x=button_x, y=self.h-30)
        self.insert_btn.place(x=button_x, y=35)
        self.delete_btn.place(x=button_x, y=60)
        self.query_btn.place(x=button_x, y=85)
        self.step_btn.place(x=button_x, y=110)
        self.canvas.coords(self.mode_label, event.width*TABLE_SCALE+15, 15)
    
    def check_propagate_error(self, id):
        """
        Check if the insertion of a delete-min would cause another delete-min to hit the ceiling. This check is done by using an existing delete-min; it will ignore its current pair and propagate to the next lowest available insert.

        :param id: tkinter ID of the delete-min line
        """
        [t, y, _, _] = self.line_quantized_coords[id]
        if y >= 9/10*self.vertical_space:
            miny = -1
            minid = -1
            for line in self.crossids:
                c = self.line_quantized_coords[line]
                if c[0] <= t and c[2]>t:
                    if c[1] > miny:
                        miny = c[1]
                        minid = line

            if miny < 0:
                return True
            else:
                if minid in self.pairs:
                    return self.check_propagate_error(self.pairs[minid])
                else:
                    return False


    def motion(self, event):
        """
        Respond to mouse motion. In insert mode, there is a shadow ray that is blue if the insert is allowed and red otherwise. Motion in the bottom bar corresponds to an upward ray; otherwise, there is a horizontal ray. In delete mode, hovering over an existing line turns the lines red or blue, depending on if the deletion is allowed. In query mode, motion triggers a query of the current t location of the mouse.

        :param event: tkinter event, holding location of mouse
        """

        if event.x >= self.w * TABLE_SCALE - 5:
            if self.last_highlight != -1:
                self.canvas.itemconfig(self.last_highlight, fill='black')
                if self.last_highlight in self.crossids:
                    self.canvas.itemconfig(self.linedotid[self.last_highlight], fill='black', outline='black')
            if self.ghost_ray is not None:
                self.canvas.delete(self.ghost_ray)
                self.ghost_ray = None
            if self.ghost_dot is not None:
                self.canvas.delete(self.ghost_dot)
                self.ghost_dot = None
            self.last_highlight = -1
            return

        if self.query_id is not None:
            self.canvas.delete(self.query_id)
            self.query_id = None

        if self.mode == "query":
            t, y = self.quantize(event.x, event.y, self.w, self.h)
            self.display_table(t)
            curr_queue = self.query(t)
            curr_min = 0
            if len(curr_queue) > 0:
                curr_min = curr_queue[-1]
            self.query_id = self.display_line(t, VERTICAL_SCALE*self.vertical_space, t, curr_min)

            self.canvas.itemconfig(self.query_id, fill='green')
            self.canvas.itemconfig(self.table_label, text="Elements \nat t=%d:" % t)

        # color changes on hover, for "Delete" events only
        elif self.mode == "delete":
            t, y = self.quantize(event.x, event.y, self.w, self.h)
    
            closest = -1
            dist = float('inf')
            linetype = None
            for line in self.crossids:
                c = self.line_quantized_coords[line]
                if c[1] <= y+1 and c[1]>=y-1 and c[0] <= t and c[2] >= t:
                    if abs(y-c[1]) < dist:
                        closest = line
                        dist = abs(y-c[1])
                        linetype = "cross"

            for line in self.upids:
                c = self.line_quantized_coords[line]
                if c[0] <= t+1 and c[0]>=t-1 and c[3] <= y and c[1] >= y:
                    if abs(t-c[0]) < dist:
                        closest = line
                        dist = abs(t-c[0])
                        linetype = "up"

            if closest >= 0:
                if self.last_highlight != -1 and self.last_highlight != closest:
                    self.canvas.itemconfig(self.last_highlight, fill='black')
                    if self.last_highlight in self.crossids:
                        self.canvas.itemconfig(self.linedotid[self.last_highlight], fill='black', outline='black')
                else:
                    if linetype == "up":
                        self.canvas.itemconfig(closest, fill='light blue')
                        if self.last_highlight in self.crossids:
                            self.canvas.itemconfig(self.linedotid[self.last_highlight], fill='light blue', outline='light blue')
                    elif linetype == "cross":
                        if closest in self.pairs and self.check_propagate_error(self.pairs[closest]):
                            self.canvas.itemconfig(closest, fill='red')
                            self.canvas.itemconfig(self.linedotid[closest], fill='red', outline='red')
                        else:
                            self.canvas.itemconfig(closest, fill='light blue')
                            self.canvas.itemconfig(self.linedotid[closest], fill='light blue', outline='light blue')
                            
                self.last_highlight = closest

            else:
                if self.last_highlight != -1:
                    self.canvas.itemconfig(self.last_highlight, fill='black')
                    if self.last_highlight in self.crossids:
                        self.canvas.itemconfig(self.linedotid[self.last_highlight], fill='black', outline='black')
                self.last_highlight = -1

        elif self.mode == "insert":
            t, y = self.quantize(event.x, event.y, self.w, self.h)

            linecoords = []

            # turn ghost red if coordinate is taken
            red = False
            if t in self.taken_x or y in self.taken_y:
                red = True

            # insert a delete-min
            if y >= VERTICAL_SCALE*self.vertical_space:
                miny = -1
                minid = -1
                for line in self.crossids:
                    c = self.line_quantized_coords[line]
                    if c[0] <= t and c[2]>=t:
                        if c[1] > miny:
                            miny = c[1]
                            minid = line

                if miny < 0:
                    linecoords = [t, round(VERTICAL_SCALE*self.vertical_space), t, 0]
                    red = True
                else:
                    linecoords = [t, round(VERTICAL_SCALE*self.vertical_space), t, miny]
                    if minid in self.pairs:
                        red = self.check_propagate_error(self.pairs[minid])

            #insert line
            else:
                mint = self.w + 1
                minid = -1
                for line in self.upids:
                    c = self.line_quantized_coords[line]
                    if c[3] <= y and c[1]>=y:
                        if c[0] < mint and c[0] > t:
                            mint = c[0]
                            minid = line

                # doesn't cross a line
                if minid == -1:
                    linecoords = [t, y, self.horizontal_space, y]
                # crosses a line
                else:
                    linecoords = [t, y, mint, y]

            if self.ghost_ray is None:
                if red:
                    self.ghost_ray = self.display_line(linecoords[0], linecoords[1], linecoords[2], linecoords[3], fill="red")
                else:
                    self.ghost_ray = self.display_line(linecoords[0], linecoords[1], linecoords[2], linecoords[3], fill="light blue")
            else:
                pt1 = self.unquantize(linecoords[0], linecoords[1], self.w, self.h)
                pt2 = self.unquantize(linecoords[2], linecoords[3], self.w, self.h)

                self.canvas.coords(self.ghost_ray, pt1[0], pt1[1], pt2[0], pt2[1])

                if red:
                    self.canvas.itemconfig(self.ghost_ray, fill='red')
                else:
                    self.canvas.itemconfig(self.ghost_ray, fill='light blue')

            if y >= 9/10*self.vertical_space:
                if self.ghost_dot is not None:
                    self.canvas.delete(self.ghost_dot)
                    self.ghost_dot = None
            elif self.ghost_dot is None:
                if red:
                    self.ghost_dot = self.display_dot(linecoords[0], linecoords[1], fill="red", outline="red")
                else:
                    self.ghost_dot = self.display_dot(linecoords[0], linecoords[1], fill="light blue", outline="light blue")
            else:
                pt = self.unquantize(linecoords[0], linecoords[1], self.w, self.h)        
                self.canvas.coords(self.ghost_dot, pt[0]+3, pt[1]+3, pt[0]-3, pt[1]-3)
                if red:
                    self.canvas.itemconfig(self.ghost_dot, fill='red', outline='red')
                else:
                    self.canvas.itemconfig(self.ghost_dot, fill='light blue', outline='light blue')


    def clicked(self, event):
        """
        Respond to mouse clicks. In insert and delete mode, if the action is valid, a ray will be inserted or deleted.

        :param event: tkinter event, holding location of mouse
        """
        if event.x >= self.w * TABLE_SCALE - 5:
            return

        x, y = self.quantize(event.x, event.y, self.w, self.h)

        # avoid drawing lines too close to edge
        if (x < 4 or x > self.horizontal_space-4) and (y < 4 or y > self.vertical_space - 4) and (event.x < 24 or event.x > self.w * TABLE_SCALE - 24) and (event.y < 24 or event.y > self.h - 24):
            return

        if self.mode == "query":
            print([round(VERTICAL_SCALE*self.vertical_space-l) for l in self.query(x)])
        elif self.mode == "insert":
            self.insert(x, y)
            self.display_table()
        elif self.mode == "delete":
            self.delete(x, y)
            self.display_table()

    def toggle_delete(self):
        """
        Helper function; toggles to delete mode from a button press.
        """
        self.toggle(None, "d")

    def toggle_insert(self):
        """
        Helper function; toggles to insert mode from a button press.
        """
        self.toggle(None, "i")

    def toggle_step(self):
        """
        Helper function; toggles stepthrough mode from a button press.
        """
        self.toggle(None, "s")

    def toggle_query(self):
        """
        Helper function; toggles to query mode from a button press.
        """
        self.toggle(None, "q")

    def toggle(self, event, key=None):
        """
        Toggles between modes; resets some values and erases shadow rays.
        """
        if key is None:
            key = event.keysym
        if time.time() - self.last_toggle > .1:
            print(key)
            self.last_toggle = time.time()
            if key == "d":
                self.mode = "delete"
                self.delete_btn.select()
                self.insert_btn.deselect()
                self.query_btn.deselect()
            elif key == "i":
                self.mode = "insert"
                self.delete_btn.deselect()
                self.insert_btn.select()
                self.query_btn.deselect()
            elif key == "q":
                self.mode = "query"
                self.delete_btn.deselect()
                self.insert_btn.deselect()
                self.query_btn.select()
            elif key == "s":
                self.step = not self.step
                if self.step:
                    self.step_btn.configure(fg="green")
                else:
                    self.step_btn.configure(fg="black")
                print("step-through: ", self.step)
            if self.last_highlight != -1:
                self.canvas.itemconfig(self.last_highlight, fill='black')
                if self.last_highlight in self.crossids:
                    self.canvas.itemconfig(self.linedotid[self.last_highlight], fill='black', outline='black')
            if self.ghost_ray is not None:
                self.canvas.delete(self.ghost_ray)
                self.ghost_ray = None
            if self.ghost_dot is not None:
                self.canvas.delete(self.ghost_dot)
                self.ghost_dot = None
            self.last_highlight = -1
            self.display_table()
            self.canvas.itemconfig(self.table_label, text="Elements \nat t=∞:")

    def insert(self, t, y):
        """
        Insert a delete-min or an insert. Nothing is done if the action is invalid.

        :param t: quantized t coordinate of the mouse click
        :param y: quantized y coordinate of the mouse click
        """

        # don't allow same coords
        if t in self.taken_x or y in self.taken_y:
            return
        # "Insert" of a delete-min event of value y at time t
        if y >= VERTICAL_SCALE*self.vertical_space:
            miny = -1
            minid = -1
            for line in self.crossids:
                c = self.line_quantized_coords[line]
                if c[0] <= t and c[2]>=t:
                    if c[1] > miny:
                        miny = c[1]
                        minid = line

            if miny < 0:
                print("No min to delete")
                return
            elif minid in self.pairs:
                if self.check_propagate_error(self.pairs[minid]):
                    return

            id = self.display_line(t, round(VERTICAL_SCALE*self.vertical_space), t, miny)
            self.upids.add(id)

            self.line_quantized_coords[id] = [t, round(VERTICAL_SCALE*self.vertical_space), t, miny]
            c = self.line_quantized_coords[minid]
            self.taken_x.add(t)
            self.line_quantized_coords[minid][2] = t
            self.scale_line(minid)
            # need to propagate
            if minid in self.pairs:
                c_to_replace = self.line_quantized_coords[self.pairs[minid]]
                self.canvas.delete(self.pairs[minid])
                del self.line_quantized_coords[self.pairs[minid]]
                self.taken_x.remove(c_to_replace[0])

                self.upids.remove(self.pairs[minid])
                del self.pairs[self.pairs[minid]]

                self.pairs[id] = minid
                self.pairs[minid] = id
                if self.step:
                    self.canvas.after(100, lambda: self.insert(c_to_replace[0], c_to_replace[1]))
                else:
                    self.insert(c_to_replace[0], c_to_replace[1])
            else:
                self.pairs[id] = minid
                self.pairs[minid] = id

        #insert line
        else:
            mint = self.w + 1
            minid = -1
            for line in self.upids:
                c = self.line_quantized_coords[line]
                if c[3] <= y and c[1]>=y:
                    if c[0] < mint and c[0] > t:
                        mint = c[0]
                        minid = line

            # doesn't cross a line
            if minid == -1:
                id = self.display_line(t, y, self.horizontal_space, y)
                self.line_quantized_coords[id] = [t, y, self.horizontal_space, y]
                id2 = self.display_dot(t, y)
                self.crossids.add(id)
                self.dot_quantized_coords[id2] = [t, y]
                self.linedotid[id] = id2
                self.taken_x.add(t)
                self.taken_y.add(y)

            # crosses a line
            else:
                id = self.display_line(t, y, mint, y)
                id2 = self.display_dot(t, y)
                self.line_quantized_coords[id] = [t, y, mint, y]
                self.crossids.add(id)
                self.linedotid[id] = id2
                self.taken_x.add(t)
                self.taken_y.add(y)
                self.dot_quantized_coords[id2] = [t, y]
                self.line_quantized_coords[minid][3] = y
                self.scale_line(minid)

                # need to propagate
                if minid in self.pairs:
                    c_to_replace = self.line_quantized_coords[self.pairs[minid]]
                    self.canvas.delete(self.pairs[minid])
                    del self.line_quantized_coords[self.pairs[minid]]

                    self.canvas.delete(self.linedotid[self.pairs[minid]])
                    del self.dot_quantized_coords[self.linedotid[self.pairs[minid]]]
                    del self.linedotid[self.pairs[minid]]
                    self.taken_x.remove(c_to_replace[0])
                    self.taken_y.remove(c_to_replace[1])

                    self.crossids.remove(self.pairs[minid])
                    del self.pairs[self.pairs[minid]]
                    self.pairs[id] = minid
                    self.pairs[minid] = id
                    if self.step:
                        self.canvas.after(100, lambda: self.insert(c_to_replace[0], c_to_replace[1]))
                    else:
                        self.insert(c_to_replace[0], c_to_replace[1])
                else:
                    self.pairs[id] = minid
                    self.pairs[minid] = id

        self.display_table()

    def delete(self, t, y):
        """
        Delete a delete-min or an insert. Nothing is done if the action is invalid.

        :param t: quantized t coordinate of the mouse click
        :param y: quantized y coordinate of the mouse click
        """
        # Delete a deletemin
        if self.last_highlight in self.upids:
            if self.last_highlight != -1:
                self.canvas.delete(self.last_highlight)
                c = self.line_quantized_coords[self.last_highlight]
                del self.line_quantized_coords[self.last_highlight]
                self.taken_x.remove(c[0])

                c_to_replace = self.line_quantized_coords[self.pairs[self.last_highlight]]
                self.canvas.delete(self.pairs[self.last_highlight])
                del self.line_quantized_coords[self.pairs[self.last_highlight]]
                
                self.crossids.remove(self.pairs[self.last_highlight])
                self.canvas.delete(self.linedotid[self.pairs[self.last_highlight]])
                self.taken_x.remove(c_to_replace[0])
                self.taken_y.remove(c_to_replace[1])
                del self.linedotid[self.pairs[self.last_highlight]]

                self.upids.remove(self.last_highlight)
                del self.pairs[self.pairs[self.last_highlight]]
                del self.pairs[self.last_highlight]
                self.last_highlight = -1
                if self.step:
                    self.canvas.after(100, lambda: self.insert(c_to_replace[0], c_to_replace[1]))
                else:
                    self.insert(c_to_replace[0], c_to_replace[1])

        # Delete an insert
        else:
            if self.last_highlight != -1:
                # has pair; need to propagate
                if self.last_highlight in self.pairs:
                    if self.check_propagate_error(self.pairs[self.last_highlight]):
                        return

                    self.canvas.delete(self.last_highlight)
                    c = self.line_quantized_coords[self.last_highlight]
                    self.taken_x.remove(c[0])
                    self.taken_y.remove(c[1])
                    del self.line_quantized_coords[self.last_highlight]
                    
                    c_to_replace = self.line_quantized_coords[self.pairs[self.last_highlight]]
                    self.canvas.delete(self.pairs[self.last_highlight])
                    self.canvas.delete(self.linedotid[self.last_highlight])
                    del self.linedotid[self.last_highlight]
                    self.crossids.remove(self.last_highlight)
                    self.upids.remove(self.pairs[self.last_highlight])
                    del self.pairs[self.pairs[self.last_highlight]]
                    del self.pairs[self.last_highlight]
                    self.last_highlight = -1
                    self.taken_x.remove(c_to_replace[0])
                    if self.step:
                        self.canvas.after(100, lambda: self.insert(c_to_replace[0], c_to_replace[1]))
                    else:
                        self.insert(c_to_replace[0], c_to_replace[1])

                # doesn't have pair
                else:
                    self.canvas.delete(self.last_highlight)
                    c = self.line_quantized_coords[self.last_highlight]
                    self.taken_x.remove(c[0])
                    self.taken_y.remove(c[1])
                    del self.line_quantized_coords[self.last_highlight]

                    self.canvas.delete(self.linedotid[self.last_highlight])
                    del self.dot_quantized_coords[self.linedotid[self.last_highlight]]
                    del self.linedotid[self.last_highlight]
                    self.crossids.remove(self.last_highlight)

                    self.last_highlight = -1

        self.display_table()


if __name__ == "__main__":

    # splash screen; 

    splash = tk.Tk()

    splash.title("rpqvis")
    ws = splash.winfo_screenwidth()
    hs = splash.winfo_screenheight()
    x = (ws/2) - 300
    y = (hs/2) - 150
    splash.geometry("600x300+%d+%d" % (x, y))


    splash_label= tk.Label(splash, text= "rpqvis", fg= "black", font = ('TkDefaultFont', 40)).pack(pady=60)
    click_label = tk.Label(splash, text= "click to begin", fg= "black", font = ('TkDefaultFont', 20)).pack(pady=20)

    def mainWin(_=None):
        x = splash.winfo_x()
        y = splash.winfo_y()
        splash.destroy()
        Window(x, y)

    splash.bind("<Button-1>", mainWin)
    # splash.after(3000, mainWin)
    splash.minsize(600, 300)
    splash.maxsize(600, 300)

    splash.mainloop()