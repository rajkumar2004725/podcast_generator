from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

def create_test_pdf():
    # Create the PDF
    c = canvas.Canvas("test_article.pdf", pagesize=letter)
    
    # Set font and size
    c.setFont("Helvetica", 12)
    
    # Add title
    c.drawString(72, 750, "The Future of AI")
    
    # Add content
    text = """
    Artificial Intelligence has made remarkable progress in recent years. From language 
    models to robotics, AI is transforming how we live and work. This technology offers 
    immense potential for solving complex problems and improving human life.

    Key developments include:
    1. Large Language Models
    2. Computer Vision
    3. Autonomous Systems

    As we look ahead, responsible AI development and ethical considerations will be 
    crucial for ensuring these technologies benefit society as a whole.
    """
    
    # Split text into lines and draw them
    y = 700
    for line in text.split('\n'):
        if line.strip():
            c.drawString(72, y, line.strip())
            y -= 20
    
    # Save the PDF
    c.save()

if __name__ == "__main__":
    create_test_pdf()
