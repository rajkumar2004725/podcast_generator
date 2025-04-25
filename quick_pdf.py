from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

def create_pdf():
    # Create a new PDF with letter size
    c = canvas.Canvas("test_article.pdf", pagesize=letter)
    
    # Read the text content
    with open("test_article.txt", "r", encoding="utf-8") as file:
        text = file.read()
    
    # Add text to the PDF
    c.drawString(72, 800, text)  # Starting at x=72, y=800
    
    # Save the PDF
    c.save()

if __name__ == "__main__":
    create_pdf()
