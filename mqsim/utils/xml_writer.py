class XmlWriter:
    def __init__(self):
        self.buffer = '<?xml version="1.0" encoding="us-ascii"?>\n'
        self.indent_level = 0
        self.tag_stack = []
        self.tag_opened = False

    def write_open_tag(self, name):
        if self.tag_opened:
            self.buffer += ">\n"
        
        self.buffer += '\t' * self.indent_level + f'<{name}'
        self.tag_stack.append(name)
        self.indent_level += 1
        self.tag_opened = True

    def write_close_tag(self):
        self.indent_level -= 1
        name = self.tag_stack.pop()
        
        if self.tag_opened:
            self.buffer += "/>\n"
        else:
            self.buffer += '\t' * self.indent_level + f'</{name}>\n'
        
        self.tag_opened = False

    def write_attribute_string(self, name, value):
        if not self.tag_opened:
            # Technically invalid usage if tag already closed, but we'll just append
            pass
        self.buffer += f' {name}="{value}"'

    def save_to_file(self, file_path):
        # Close any lingering tags
        while self.tag_stack:
            self.write_close_tag()
            
        with open(file_path, "w") as f:
            f.write(self.buffer)
