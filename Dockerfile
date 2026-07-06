FROM python:3.12-slim

# Binaires système : ffmpeg (montage), poppler (pdfunite/pdfimages/pdftotext), polices
RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg poppler-utils fonts-liberation ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Le moteur vidéo attend des polices Arial aux chemins macOS -> on redirige vers Liberation Sans
RUN mkdir -p "/System/Library/Fonts/Supplemental" && \
    ln -sf /usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf "/System/Library/Fonts/Supplemental/Arial.ttf" && \
    ln -sf /usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf    "/System/Library/Fonts/Supplemental/Arial Bold.ttf" && \
    ln -sf /usr/share/fonts/truetype/liberation/LiberationSans-Italic.ttf  "/System/Library/Fonts/Supplemental/Arial Italic.ttf"

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PORT=8765
EXPOSE 8765
CMD ["python3", "backend/server.py"]
