          
from io import StringIO

class StringIOLineBreak(StringIO):
    def __init__(self, *args, markup=None,  **kwargs):
        self._markup = markup
        super().__init__(*args, **kwargs)
    
    def write(self, s:str):
        s = s + '\n'
        super().write(s)
        
    def write_indented(self, s:str):
        s = '    ' + s + '\n'
        super().write(s)
        
    def title1(self, s):
        if self._markup == 'rich':
            s = f'[bold][underline]{s}[/underline][/bold]'
        elif self._markup == 'kivy':
            s = f'[b][u]{s}[/u][/b]'
        elif self._markup == 'html':
            s = f'<h1>{s}</h1>'
        self.new_section()
        self.write(s)  
        
    def title2(self, s):
        if self._markup == 'rich':
            s = f'[bold]{s}[/bold]'
        elif self._markup == 'kivy':
            s = f'[b]{s}[/b]'
        elif self._markup == 'html':
            s = f'<h2>{s}</h2>'
        self.new_paragraph()
        self.write(s) 
        
    def key_value(self, k, v):
        if not k:
            self.write_indented(v)
            return
            
        if self._markup == 'rich':
            s = f'[bold]{k}[/bold]:  {v}'
        elif self._markup == 'kivy':
            s = f'[b]{k}[/b]:  {v}'
        elif self._markup == 'html':
            s = f'<b>{k}</b>:  {v}'
        self.write_indented(s)
        
    def link(self, s, link):
        if self._markup == 'rich':
            s = f'[bold]{s}[/bold]:  [link={link}]{link}[/link] '
        elif self._markup == 'kivy':
            s = f'[b]{s}[/b]:  [ref={link}]{link}[/ref]'
        elif self._markup == 'html':
            s = f'<b>{s}</b>: <a href={link}>{link}</a>' 
        self.write_indented(s)
        
    
    def new_paragraph(self):
        super().write('\n')    
    
    def new_section(self):
        super().write('\n\n')