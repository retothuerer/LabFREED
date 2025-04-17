
class DataTable(list):
    def __init__(self, col_names:list[str]=None):
        self.col_names = col_names
        self.row_template = None
        super().__init__()
    
    def append(self, row:list):
        if not self.row_template:
            self.row_template = row.copy()
        super().append(row)
        
    def extend(self, iterable):
        for item in iterable:
            self.append(item) 
        
        

    