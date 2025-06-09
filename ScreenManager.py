from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout

# Tela principal (Main)
class MainScreen(Screen):
    def __init__(self, **kwargs):
        super(MainScreen, self).__init__(**kwargs)
        layout = BoxLayout(orientation='vertical')
        layout.add_widget(Button(text="Ir para tela de registro", on_press=self.ir_para_registro))
        self.add_widget(layout)

    def ir_para_registro(self, instance):
        self.manager.current = 'register'

# Tela de registro
class RegisterScreen(Screen):
    def __init__(self, **kwargs):
        super(RegisterScreen, self).__init__(**kwargs)
        layout = BoxLayout(orientation='vertical')
        layout.add_widget(Button(text="Voltar para tela principal", on_press=self.voltar))
        self.add_widget(layout)

    def voltar(self, instance):
        self.manager.current = 'main'

# Gerenciador de telas
class ScreenApp(App):
    def build(self):
        sm = ScreenManager()
        sm.add_widget(MainScreen(name='main'))
        sm.add_widget(RegisterScreen(name='register'))
        return sm

if __name__ == '__main__':
    ScreenApp().run()
