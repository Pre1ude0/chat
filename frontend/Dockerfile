FROM node:22-slim AS base
ENV PNPM_HOME="/pnpm"
ENV PATH="$PNPM_HOME:$PATH"
RUN corepack enable
COPY . /app/frontend
WORKDIR /app/frontend

FROM base AS prod-deps
RUN --mount=type=cache,id=pnpm,target=/pnpm/store pnpm install --prod --frozen-lockfile

FROM base AS build
RUN --mount=type=cache,id=pnpm,target=/pnpm/store pnpm install --frozen-lockfile
RUN pnpm run build


FROM base
COPY --from=prod-deps /app/frontend/node_modules /app/frontend/node_modules
COPY --from=build /app/frontend/build /app/frontend/build
EXPOSE 3000
CMD [ "node", "build/index.js"]
