# -*- coding: utf-8 -*-

"""
	Module Test : frame
"""
import PySimpleGUI as sg

"""
    Demo - Element List

    All elements shown in 1 window as simply as possible.

    Copyright 2022 PySimpleGUI
"""


use_custom_titlebar = True if sg.running_trinket() else False

def make_window(theme=None):

    NAME_SIZE = 23

    def name(name):
        dots = NAME_SIZE-len(name)-2
        return sg.Text(name + ' ' + '•'*dots, size=(NAME_SIZE,1), justification='r',pad=(0,0), font='Courier 10')

    sg.theme(theme)

    # NOTE that we're using our own LOCAL Menu element
    if use_custom_titlebar:
        Menu = sg.MenubarCustom
    else:
        Menu = sg.Menu

    treedata = sg.TreeData()

    treedata.Insert("", '_A_', 'Tree Item 1', [1234], )
    treedata.Insert("", '_B_', 'B', [])
    treedata.Insert("_A_", '_A1_', 'Sub Item 1', ['can', 'be', 'anything'], )

    layout_l = [
                [name('Text'), sg.Text('Text')],
                [name('Input'), sg.Input(s=15)],
                [name('Multiline'), sg.Multiline(s=(15,2))],
                [name('Output'), sg.Output(s=(15,2))],
                [name('Combo'), sg.Combo(sg.theme_list(), default_value=sg.theme(), s=(15,22), enable_events=True, readonly=True, k='-COMBO-')],
                [name('OptionMenu'), sg.OptionMenu(['OptionMenu',],s=(15,2))],
                [name('Checkbox'), sg.Checkbox('Checkbox')],
                [name('Radio'), sg.Radio('Radio', 1)],
                [name('Spin'), sg.Spin(['Spin',], s=(15,2))],
                [name('Button'), sg.Button('Button')],
                [name('ButtonMenu'), sg.ButtonMenu('ButtonMenu', sg.MENU_RIGHT_CLICK_EDITME_EXIT)],
                [name('Slider'), sg.Slider((0,10), orientation='h', s=(10,15))],
                [name('Listbox'), sg.Listbox(['Listbox', 'Listbox 2'], no_scrollbar=True,  s=(15,2))],
                [name('Image'), sg.Image(sg.EMOJI_BASE64_HAPPY_THUMBS_UP)],
                [name('Graph'), sg.Graph((125, 50), (0,0), (125,50), k='-GRAPH-')]  ]

    layout_r  = [[name('Canvas'), sg.Canvas(background_color=sg.theme_button_color()[1], size=(125,40))],
                [name('ProgressBar'), sg.ProgressBar(100, orientation='h', s=(10,20), k='-PBAR-')],
                [name('Table'), sg.Table([[1,2,3], [4,5,6]], ['Col 1','Col 2','Col 3'], num_rows=2)],
                [name('Tree'), sg.Tree(treedata, ['Heading',], num_rows=3)],
                [name('Horizontal Separator'), sg.HSep()],
                [name('Vertical Separator'), sg.VSep()],
                [name('Frame'), sg.Frame('Frame', [[sg.T(s=15)]])],
                [name('Column'), sg.Column([[sg.T(s=15)]])],
                [name('Tab, TabGroup'), sg.TabGroup([[sg.Tab('Tab1',[[sg.T(s=(15,2))]]), sg.Tab('Tab2', [[]])]])],
                [name('Pane'), sg.Pane([sg.Col([[sg.T('Pane 1')]]), sg.Col([[sg.T('Pane 2')]])])],
                [name('Push'), sg.Push(), sg.T('Pushed over')],
                [name('VPush'), sg.VPush()],
                [name('Sizer'), sg.Sizer(1,1)],
                [name('StatusBar'), sg.StatusBar('StatusBar')],
                [name('Sizegrip'), sg.Sizegrip()]  ]

    # Note - LOCAL Menu element is used (see about for how that's defined)
    layout = [[Menu([['File', ['Exit']], ['Edit', ['Edit Me', ]]],  k='-CUST MENUBAR-',p=0)],
              [sg.T('PySimpleGUI Elements - Use Combo to Change Themes', font='_ 14', justification='c', expand_x=True)],
              [sg.Checkbox('Use Custom Titlebar & Menubar', use_custom_titlebar, enable_events=True, k='-USE CUSTOM TITLEBAR-', p=0)],
              [sg.Col(layout_l, p=0), sg.Col(layout_r, p=0)]]

    window = sg.Window('The PySimpleGUI Element List', layout, finalize=True, right_click_menu=sg.MENU_RIGHT_CLICK_EDITME_VER_EXIT, keep_on_top=True, use_custom_titlebar=use_custom_titlebar)

    window['-PBAR-'].update(30)                                                     # Show 30% complete on ProgressBar
    window['-GRAPH-'].draw_image(data=sg.EMOJI_BASE64_HAPPY_JOY, location=(0,50))   # Draw something in the Graph Element

    return window

def make_frame():
	my_list = ['item0', 'item1', 'item2', 'item3']
	my_combo = sg.Combo(my_list, default_value = my_list[0], enable_events = True, key = '-MY_COMBO-')
	my_text = sg.Text("This is my choice:")
	my_input = sg.Input("My choice here", key = '-MY_CHOICE-')
	my_slider = sg.Slider(range = (0, 4), default_value = 2, orientation = 'horizontal', key = '-MY_SLIDER-')
	my_frame = sg.Frame("My frame", [[my_combo, my_text, my_input], [my_slider]])
	
	window = sg.Window("My window", [[my_frame]], finalize = True, enable_close_attempted_event = True)
	
	return window

def make_frame_with_tab():
	my_list = ['item0', 'item1', 'item2', 'item3']
	my_combo1 = sg.Combo(my_list, default_value = my_list[0], enable_events = True, key = '-MY_COMBO1-', readonly = True)
	my_combo2 = sg.Combo(my_list, default_value = my_list[0], enable_events = True, key = '-MY_COMBO2-', readonly = True)
	my_text1 = sg.Text("This is my choice:")
	my_text2 = sg.Text("This is my choice:")
	my_input1 = sg.Input("My choice here", key = '-MY_CHOICE1-')
	my_input2 = sg.Input("My choice here", key = '-MY_CHOICE2-')
	my_slider1 = sg.Slider(range = (0, 20), default_value = 2, orientation = 'horizontal', key = '-MY_SLIDER1-', disabled = True, visible = False)
	my_slider2 = sg.Slider(range = (0, 20), default_value = 2, orientation = 'horizontal', key = '-MY_SLIDER2-', disabled = True, visible = False)
	my_button1 = sg.Button('My button', key = '-MY_BUTTON1-')
	my_button2 = sg.Button('My button', key = '-MY_BUTTON2-')
	my_tab1 = sg.Tab('Tab1', [[sg.Text('This tab is empty')]], key = '-TAB1-')
	my_tab2 = sg.Tab('Tab2', [[my_combo1, my_text1, my_input1], [my_slider1, sg.Push()], [my_button1]], key = '-TAB2-')
	my_tab3 = sg.Tab('Tab3', [[sg.Text('This tab is empty')]], key = '-TAB3-')
	my_tab4 = sg.Tab('Tab4', [[my_combo2, my_text2, my_input2], [my_slider2, sg.Push()], [my_button2]], key = '-TAB4-')
	my_tabgroup1 = sg.TabGroup([[my_tab1, my_tab2]], key = '-MY_TABGROUP1-', enable_events = True)
	my_tabgroup2 = sg.TabGroup([[my_tab3, my_tab4]], key = '-MY_TABGROUP2-', enable_events = True)
	my_frame1 = sg.Frame("My frame 1", [[my_tabgroup1]])
	my_frame2 = sg.Frame("My frame 2", [[my_tabgroup2]])
	
	window = sg.Window("My window", [[my_frame1], [my_frame2]], finalize = True, enable_close_attempted_event = True)
	
	return window

# Main function
#--------------
def main():
	window = make_window()

	while True:
		event, values = window.read()
		# sg.Print(event, values)
		if event == sg.WIN_CLOSED or event == 'Exit':
			break
		if event == 'Edit Me':
			sg.execute_editor(__file__)
		if values['-COMBO-'] != sg.theme():
			sg.theme(values['-COMBO-'])
			window.close()
			window = make_window()
		if event == '-USE CUSTOM TITLEBAR-':
			use_custom_titlebar = values['-USE CUSTOM TITLEBAR-']
			sg.set_options(use_custom_titlebar=use_custom_titlebar)
			window.close()
			window = make_window()
		elif event == 'Version':
			sg.popup_scrolled(sg.get_versions(), __file__, keep_on_top=True, non_blocking=True)
	window.close()

def main2():
	window = make_frame_with_tab()
	
	while True:
		event, values = window.read()
		if event == sg.WINDOW_CLOSE_ATTEMPTED_EVENT:
			break
	
	window.close()

# Main program,
# running only if the module is NOT imported (but directly executed)
#-------------------------------------------------------------------
if __name__ == '__main__':
	main2()
	