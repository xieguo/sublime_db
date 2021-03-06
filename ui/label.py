
from sublime_db.core.typecheck import (
	Optional,
	List
)

from .layout import Layout
from .component import ComponentInline, components

html_escape_table = {
	"&": "&amp;",
	">": "&gt;",
	"<": "&lt;",
}

def html_escape(text: str) -> str:
    """Produce entities within text."""
    return "".join(html_escape_table.get(c,c) for c in text)

class Label(ComponentInline):
	def __init__(self, text: Optional[str], color: str = "primary", align: float = 0.5, width: Optional[float] = None, padding_left = 0, padding_right = 0) -> None:
		super().__init__()
		if text:
			self.text = text.replace("\u0000", "\\u0000")
		else:
			self.text = ""
			
		self.align = align
		self.width = width
		self.padding_left = padding_left
		self.padding_right = padding_right
		if color:
			self.add_class(color)
		self.render_text = ""

	def render(self) -> components:
		layout = self.layout
		assert layout, '??'
		align = self.align
		max_size = self.width
		self.render_text = self.text
		if max_size:
			emWidth = layout.em_width()
			count = max_size / emWidth
			self.render_text = self.render_text[0:int(count)]
		if self.width:
			length = len(self.render_text)
			emWidth = layout.em_width()
	
			leftover = self.width - (length) * emWidth
			self.paddingleft = leftover * align
			self.paddingright = leftover * (1.0 - align)

		else:
			self.paddingright = 0
			self.paddingleft = 0
		
		self.paddingleft += self.padding_left
		self.paddingright += self.padding_right
		self.render_text = html_escape(self.render_text) or ""
		self.html_tag_extra = 'style="padding-left:{}rem; padding-right:{}rem;"'.format(self.paddingleft, self.paddingright)
		return []

	def html_inner(self, layout: Layout) -> str:
		return self.render_text