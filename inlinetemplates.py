## code-level templates
# (Mr. Lazy)

from django.utils.safestring import mark_safe
from django.utils import html
import math



class TreeRender():
    '''
    Render tree iters as a 2D graphics tree in HTML/SVG.
    
    The styles should be provides as SVG format e.g. 
    'stroke:rgb(0,220,126);stroke-width:4;'
    '''
    text_style = ''
    beam_style = 'stroke:black;stroke-width:4;'
    stem_style = 'stroke:black;stroke-width:2;'
    
    def text_template(self, x, y, cb_data):
        return ('<text x="{0}" y="{1}">{2}</text>').format(x, y, cb_data)

    def svg_template(self, width, height):
        return ('<svg width="{0}" height="{1}">').format(width, height)

    def rend_default_horizontal(
          self, 
          tree_iter, 
          x_space,
          data_height,
          data_callback
        ):
        '''
        Render the tree with a set of defaults based on the height of
        the data to be displayed.
        '''
        return self.rend(
          tree_iter, 
          x_space, 
          data_height * 4, 
          data_height * 1.5, 
          data_height * 2.5, 
          data_height,
          data_callback
        )

    def rend(self, 
        tree_iter, 
        x_space, 
        y_space, 
        stem_offset,
        beam_offset,
        graphic_offset,
        data_callback
        ):
        '''
        Render a tree as 2D SVG.
        height and width of the finished tree are claulated on the fly
        (can not be provided as initial constraints).
        
        @param x_space at least the largest width of data to be printed
        @param y_space at least the largest height of data to be 
        printed, plus beam space. For horizontal text, 4 * text hight
        is a good start.
        @param stem_offset y clearance before the stem starts. For
        horizontal text, 1.5 * text hight is a good start.
        @param beam_offset height above data for the beam. For
        horizontal text, 2.5 * text hight is a good start.
        @param graphic_offset x offset of all stem/beam graphics. For
        horizontal text, text hight is a good start.
        @param data_callback signature is callback(pk), return data is 
        rendered at each tree node.
        @return an SVG definition, suitable for embedding in an HTML
        document
        '''
        depth = 0
        x = 0
        y = 0
        ## The dummy div is filled later when the height can be calculated 
        b = ['dummy_div']
        depth_x_memory = [0 for x in range(20)]
        prev_depth = 0
        x_max = x
        y_max = y
        for depth, pk in tree_iter:
            y = ((depth) * y_space)
            y_max = max(y_max, y)
            if(depth > prev_depth):
                # it's a child
                # remember where this layer was positioned
                depth_x_memory[prev_depth] = x
                # do not move x 
            elif(depth < prev_depth):
                # it's a return to lower taxonomies
                # need to go one beyond current max
                x = x_max + x_space
                # note the max extent
                x_max = x
                # need a beam line from the previous position. This item
                # is always a sibling
                x_start = depth_x_memory[depth]
                b.append('<line x1="{0}" y1="{2}" x2="{1}" y2="{2}" style="{3}" />'.format(x_start+ graphic_offset, x+ graphic_offset, y - beam_offset, self.beam_style))
            else:
                # it's a sibling
                # move x along
                x_start = x
                x = x + x_space
                x_max = max(x_max, x)
                # print beam line from prev x to this
                b.append('<line x1="{0}" y1="{2}" x2="{1}" y2="{2}" style="{3}" />'.format(x_start+ graphic_offset, x+ graphic_offset, y - beam_offset, self.beam_style))
            #  print a stem line
            b.append('<line x1="{0}" y1="{1}" x2="{0}" y2="{2}" style="{3}" />'.format(x + graphic_offset, y - stem_offset, y - beam_offset, self.stem_style))
            b.append('<text x="{0}" y="{1}">{2}</text>'.format(x, y, data_callback(pk)))   
            b.append(self.text_template(x, y, data_callback(pk)))   
            prev_depth = depth
        b.append('</svg>')
        b[0] = self.svg_template(x_max + x_space, y_max + math.floor(y_space / 2))
        return ''.join(b)
  
     
      
class AnchorTreeRender(TreeRender):
    '''
    Requires the callback on the renders to be provided as a list of
    tuples [(href, text)]
    '''
    def text_template(self, x, y, cb_data):
        return ('<a xlink:href="{2}"><text x="{0}" y="{1}">{3}</text></a>').format(x, y, cb_data[0], cb_data[1])

    def svg_template(self, width, height):
        return ('<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" version="1.1" width="{0}" height="{1}">').format(width, height)
     
     
       

def link(text, href, attrs={}):
    '''
    Build HTML for a anchor/link.
    
    @param title escaped
    @param href escaped
    @param attrs dict of HTML attributes. Not escaped
    '''
    #NB 'attrs' can not use kwargs because may want to use reserved words
    # for keys, such as 'id' and 'class'
    b = []
    for k,v in attrs.items():
        b.append('{0}={1}'.format(k, v))
    return mark_safe('<a href="{0}" {1}/>{2}</a>'.format(
        html.escape(href),
        ' '.join(b),
        html.escape(text)
        ))

def submit(value, name, attrs={}):
    '''
    Build HTML for a anchor/link.
    
    @param title escaped
    @param name escaped
    @param attrs dict of HTML attributes. Not escaped
    '''
    #NB 'attrs' can not use kwargs because may want to use reserved words
    # for keys, such as 'id' and 'class'
    b = []
    for k,v in attrs.items():
        b.append('{0}={1}'.format(k, v))
    return mark_safe('<input name="{0}" value={1} type="submit" {2}>'.format(
        html.escape(name),
        html.escape(value),
        ' '.join(b)
        ))

# currently unused
def table_row(row_data):
    '''
    Build HTML for a table row.
    
    @param row_data Not escaped.
    @return list of the data. Needs joining.
    '''
    b = []
    for e in row_data:
        b.append('<td>')
        b.append(e)
        b.append('</td>')
    return b

def tmpl_instance_message(msg, title):
  '''Template for a message or title about an model instance'''
  return mark_safe('{0} <i>{1}</i>.'.format(msg, html.escape(title)))
  
