import webbrowser
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button
from kivy_garden.zbarcam import ZBarCam
from kivy.uix.scrollview import ScrollView

from kivy.graphics import Color, Rectangle


from test_app import Demo_Labfreed_App_Infrastructure


class ColoredBox(BoxLayout):
    def __init__(self, color=(1, 1, 1, 1), **kwargs):
        super().__init__(**kwargs)
        with self.canvas.before:
            Color(*color)
            self._rect = Rectangle()
        self.bind(pos=self._update_rect, size=self._update_rect)

    def _update_rect(self, *args):
        self._rect.pos = self.pos
        self._rect.size = self.size

class QRScannerUI(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation='vertical', **kwargs)

        # Camera gets 20% of vertical space
        
        cam_wrapper = ColoredBox(color=(1, 0, 0, 0.3), size_hint_y=0.2)  # Red, semi-transparent
        self.cam = ZBarCam()
        self.cam.bind(symbols=self.on_symbols)
        cam_wrapper.add_widget(self.cam)
        self.add_widget(cam_wrapper)
        
        
        # Label for text (80% height)
        self.text_label = Label(
            text="",
            valign='top',
            halign='left',
            size_hint_y=0.8,
            text_size=(0, None), 
            markup=True
        )

        # Ensure text aligns to top
        self.text_label.bind(
            width=lambda lbl, w: setattr(lbl, 'text_size', (w, None)),
            texture_size=lambda lbl, _: setattr(lbl, 'height', lbl.texture_size[1])
        )
        
        self.add_widget(self.text_label)
        
        
    
        self.pac_id_processor = Demo_Labfreed_App_Infrastructure()
        demo_cit ='''
origin: PERSONAL

cit:
- if: $.categories[?(@.key == "-MD")]
  entries:
  - service_type: attributes-generic
    service_name: Demo Attributes
    application_intents:
    - attributes
    template_url: http://127.0.0.1:5000
'''   
        self.pac_id_processor.add_cit(demo_cit)
        
        demo_pac = "HTTPS://PAC.METTORIUS.COM/-MD/BAL500/12345/DEMO*59K77LWDX8W"
        self.display_info(demo_pac)

    def on_symbols(self, instance, symbols):
        if symbols:
            data = symbols[0].data.decode()
            self.display_info(data)

    def display_info(self, data):
        try:
            info = self.pac_id_processor.process_pac(data, markup='kivy')
            self.text_label.text = info.__str__('kivy')
        except:
            self.text_label.text = data


class QRApp(App):
    def build(self):
        return QRScannerUI()

if __name__ == '__main__':
    QRApp().run()
