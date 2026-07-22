import pygame


def clip(surf, x, y, x_size, y_size):
    handle_surf = surf.copy()
    clipR = pygame.Rect(x, y, x_size, y_size)
    handle_surf.set_clip(clipR)
    image = surf.subsurface(handle_surf.get_clip())
    return image.copy()


def colour_swap(surf, old_c, new_c):
    img_copy = surf.copy()
    img_copy.fill(new_c)
    surf.set_colorkey(old_c)
    img_copy.blit(surf, (0, 0))
    return img_copy


# method 3
def perfect_outline_2(surf, img, loc, outline_color):
    mask = pygame.mask.from_surface(img)
    mask_outline = mask.outline()

    mask_surf = pygame.Surface(img.get_size())
    for pixel in mask_outline:
        mask_surf.set_at(pixel, outline_color)

    mask_surf.set_colorkey((0, 0, 0))
    surf.blit(mask_surf, (loc[0] - 1, loc[1]))
    surf.blit(mask_surf, (loc[0] + 1, loc[1]))
    surf.blit(mask_surf, (loc[0], loc[1] - 1))
    surf.blit(mask_surf, (loc[0], loc[1] + 1))


class Font():
    def __init__(self, path):
        self.spacing = 1
        self.character_order = self.character_order = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M',
                                                       'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z',
                                                       'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm',
                                                       'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z',
                                                       '.', '-', ',', ':', '+', '\'', '!', '?', '0', '1', '2', '3', '4',
                                                       '5', '6', '7', '8', '9', '(', ')', '/', '_', '=', '\\', '[', ']',
                                                       '*', '"', '<', '>', ';']
        font_img = pygame.image.load(path).convert()
        current_char_width = 0

        self.characters = {}
        character_count = 0

        for x in range(font_img.get_width()):

            c = font_img.get_at((x, 0))
            if c[0] == 127:
                char_img = clip(font_img, x - current_char_width, 0, current_char_width, font_img.get_height())
                self.characters[self.character_order[character_count]] = char_img.copy()
                character_count += 1
                current_char_width = 0
            else:
                current_char_width += 1

        # There's no glyph for ' ' in this font atlas format, so pick a
        # stand-in width from the loaded characters (average glyph width)
        # rather than "borrow" whatever character happened to render right
        # before the space - that breaks (UnboundLocalError in render(),
        # silently wrong width in get_width()) the moment a string STARTS
        # with a space, since there's no prior character to borrow from.
        if self.characters:
            self.space_width = sum(c.get_width() for c in self.characters.values()) / len(self.characters)
        else:
            self.space_width = 4

    def get_width(self, text, scalefactor=1):
        '''Same spacing math as render(), without drawing anything - use this
        to measure a string before laying out UI (button widths, centering,
        avoiding overlap) instead of rendering to a scratch surface.'''
        x_offset = 0
        for char in text:
            if char not in [' ', '\r']:
                char_w = self.characters[char].get_width()
                x_offset += (char_w * scalefactor + 1) + self.spacing
            elif char == '\r':
                pass
            else:
                x_offset += self.space_width * scalefactor + self.spacing
        return x_offset

    def render(self, surf, text, color, loc, scalefactor, outlinecolor, outline=True):
        '''Outline colour doesn't really matter if you set outline=False, scalefactor just scales the image by the
        scale factor '''
        x_offset = 0
        y_offset = 0
        for char in text:
            if char not in [' ', '\r']:
                text_surf = self.characters[char]

                scaledchar = pygame.transform.scale(text_surf, (
                    text_surf.get_width() * scalefactor, text_surf.get_height() * scalefactor)).copy()

                newchar = colour_swap(scaledchar, (255, 0, 0), color)
                newchar.set_colorkey((0, 0, 0))
                if outline:
                    perfect_outline_2(surf, newchar, (loc[0] + x_offset, loc[1] + y_offset), outlinecolor)
                surf.blit(newchar, (loc[0] + x_offset, loc[1] + y_offset))

                x_offset += (scaledchar.get_width() + 1) + self.spacing
            elif char == '\r':
                y_offset += 8 * scalefactor
            else:
                x_offset += self.space_width * scalefactor + self.spacing

        return x_offset
