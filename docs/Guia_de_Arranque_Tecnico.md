# Guía de Arranque Técnico — Plataforma de Adopción de Mascotas

Documento interno de trabajo. Complementa al contexto de arquitectura
(`Plataforma_de_Adopción_de_Mascotas.md`): aquí no se justifican decisiones de
AWS, se define **cómo organizar el repo, cómo estructurar CloudFormation, y en
qué orden concreto se hacen las cosas** para pasar de "nada" a un entorno
desplegado. Todo lo que sigue asume la pila ya decidida: CloudFormation (no
CDK, no SAM para producción), FastAPI + Mangum en zip, React + Vite, Lambda de
thumbnails como imagen de contenedor, CodePipeline + CodeBuild + GitHub vía
CodeStar Connection.

# 🚧En construcción 🚚...
