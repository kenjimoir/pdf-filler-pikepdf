FROM node:18

# Install Python 3 and pip for pikepdf
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip and install pikepdf
RUN python3 -m pip install --upgrade pip && \
    python3 -m pip install pikepdf

# Set working directory
WORKDIR /app

# Copy package files
COPY package*.json ./

# Install Node.js dependencies
RUN npm install

# Copy source code
COPY . .

# Make Python script executable
RUN chmod +x pdf_filler_pikepdf.py

# Expose port (Render.com uses 10000, Railway uses dynamic port)
# Use environment variable PORT or default to 8080
EXPOSE 8080

# Start the application
CMD ["node", "index.js"]

