FROM node:20-alpine

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .

# Đảm bảo quyền thực thi cho các file trong .bin
RUN chmod -R +x node_modules/.bin

CMD ["npx", "vite", "--host"]
