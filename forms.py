from django import forms



class NodeForm(forms.Form):
    #! block edit on both below
    pk = forms.IntegerField(label='Term id', min_value=0,
      disabled=True,
      help_text="Id of a category for an element."
      )
      
    title = forms.CharField(label='Term Title', max_length=64,
      disabled=True,
      help_text="Name of the category. Limited to 255 characters."
      )
      
    element = forms.IntegerField(label='Element Id', min_value=0,
      help_text="Id of an element to be categorised."
      )
      
    def __init__(self, *args, **kwargs):
      super().__init__(*args, **kwargs)
 

###

