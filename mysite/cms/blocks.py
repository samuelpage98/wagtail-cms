from wagtail import blocks
from wagtail.images.blocks import ImageChooserBlock

class HeaderStyle1Block(blocks.StructBlock):
    title = blocks.CharBlock(required=True, max_length=100)
    header_image = ImageChooserBlock(required=True)

    class Meta:
        template = 'cms/headers/header_style_1.html'

class HeaderStyle2Block(blocks.StructBlock):
    title = blocks.CharBlock(required=True, max_length=100)
    header_image = ImageChooserBlock(required=True)

    class Meta:
        template = 'cms/headers/header_style_2.html'

# Repeat for other header styles

class HeaderBlock(blocks.StreamBlock):
    header_style_1 = HeaderStyle1Block()
    header_style_2 = HeaderStyle2Block()
    # Add other header styles here
