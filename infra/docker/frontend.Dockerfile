FROM node:22-alpine
WORKDIR /app
COPY frontend/package*.json ./
RUN npm install
COPY frontend .
# NEXT_PUBLIC_* values are inlined into the client bundle when the app is built,
# so the API URL has to be present here and not only at container start.
ARG NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
RUN npm run build
CMD ["npm", "start"]
