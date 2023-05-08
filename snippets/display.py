board.DISPLAY.brightness = 0.4

# Update this to change the size of the text displayed. Must be a whole number.
scale = 2
font_height = terminalio.FONT.get_bounding_box()[1]

text_area = bitmap_label.Label(terminalio.FONT, text="Ambient: 22", scale=scale)
# text_area.x = 0.5
# text_area.y = 0.5
text_area.anchor_point = (0.5, 0.5)
text_area.anchored_position = (board.DISPLAY.width // 2, font_height * 2)
text_area.color = 0x00FFFF

text_area_2 = bitmap_label.Label(terminalio.FONT, text="Internal: 10", scale=scale)
# text_area.x = 0.5
# text_area.y = 0.5
text_area_2.anchor_point = (0.5, 0.5)
text_area_2.anchored_position = (board.DISPLAY.width // 2, board.DISPLAY.height // 2)
text_area_2.color = 0x00FFFF

text_area_3 = bitmap_label.Label(terminalio.FONT, text="Delta: -12", scale=3)
# text_area.x = 0.5
# text_area.y = 0.5
text_area_3.anchor_point = (0.5, 0.5)
text_area_3.anchored_position = (board.DISPLAY.width // 2, board.DISPLAY.height -font_height * 2)
text_area_3.color = 0x00FF00

group = displayio.Group()
group.append(text_area)
group.append(text_area_2)
group.append(text_area_3)

board.DISPLAY.show(group)
