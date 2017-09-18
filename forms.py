from django import forms



class NodeForm(forms.Form):
    #! block edit on both below
    pk = forms.IntegerField(label='Term id', min_value=0,
      #editable=False,
      help_text="A node from the model."
      )
      
    title = forms.CharField(label='Title', max_length=64,
      help_text="Name for the category. Limited to 255 characters."
      )
      
    element = forms.IntegerField(label='Elemenet', min_value=0,
      help_text="A node from the model."
      )
      
    def __init__(self, *args, **kwargs):
      super().__init__(*args, **kwargs)
 
