#version 430
uniform vec4 uHero[8];     // xy pos, z brightness, w spike
uniform float uHud[8];     // reveal 0..1
uniform float uHudDim[8];
uniform vec4 uRing;        // cx, cy, R, intensity
uniform float uZoom;
uniform float uWhite;
uniform float uFadeIn;
uniform int uNHero;
out vec4 o;

const float PSF = 0.00105;

vec3 starTint(float k){
    vec3 c = mix(vec3(0.62, 0.74, 1.0), vec3(1.0, 0.97, 0.92), smoothstep(0.0, 0.55, k));
    return mix(c, vec3(1.0, 0.72, 0.48), smoothstep(0.78, 1.0, k));
}

vec3 starLayer(vec2 uv, float cells, float zoom, int seed, float dens, float bandMask){
    vec2 p = uv / zoom * cells;
    ivec2 id = ivec2(floor(p));
    vec3 col = vec3(0.0);
    for (int j = -1; j <= 1; j++) for (int i = -1; i <= 1; i++){
        ivec2 c = id + ivec2(i, j);
        float r = h12(c + ivec2(seed * 131, 17 + seed));
        if (r > dens * (1.0 + 2.2 * bandMask)) continue;
        vec2 sp = vec2(c) + h22(c + ivec2(77 + seed, 13));
        vec2 dv = (p - sp) / cells * zoom;
        float d2 = dot(dv, dv);
        if (d2 > 0.0009) continue;
        float rb = h12(c + ivec2(5, 9 + seed));
        float b = 0.06 + pow(rb, 9.0) * 2.4;
        // ring glint
        vec2 spuv = sp / cells * zoom;
        float rd = abs(length(spuv - uRing.xy) - uRing.z);
        float gl = exp(-rd * rd / (0.016 * 0.016)) * uRing.w * step(0.01, uRing.z);
        float tw = 1.0 + 0.18 * sin(uTime * (1.5 + 3.0 * rb) + rb * 40.0);
        float sg = PSF * (0.62 + 0.5 * min(b, 1.5) + 1.4 * gl);
        float amp = b * tw * (1.0 + 7.0 * gl);
        float core = exp(-d2 / (sg * sg));
        float halo = exp(-sqrt(d2) / (sg * 3.0)) * 0.05 * min(b, 1.2);
        col += starTint(h12(c + ivec2(31, 8))) * amp * (core + halo);
    }
    return col;
}

vec3 nebula(vec2 uv, float t, out float band){
    vec2 p = uv / (1.0 + 0.006 * t);
    vec2 q = rot(-0.42) * p;
    band = exp(-q.y * q.y / 0.085);
    vec3 P = vec3(p * 2.0, t * 0.012);
    vec2 w1 = vec2(fbm(P + vec3(0, 0, 3.0), 4), fbm(P + vec3(5.2, 1.3, 3.0), 4));
    vec3 P2 = vec3(p * 2.6 + 1.5 * w1, t * 0.015 + 4.0);
    float n = fbm(P2, 6);
    float r = rfbm(P2 * 1.6 + vec3(3.0), 5);
    float cloud = smoothstep(-0.10, 0.60, n + 0.62 * band - 0.18);
    float fil = pow(r, 3.2) * cloud;
    float dust = smoothstep(0.05, 0.55, fbm(P2 * 2.3 + 9.0, 5) + 0.18);
    vec3 base = mix(vec3(0.004, 0.008, 0.028), vec3(0.016, 0.034, 0.090), cloud * cloud);
    vec3 teal = vec3(0.05, 0.30, 0.50), mag = vec3(0.50, 0.12, 0.36), amber = vec3(0.95, 0.52, 0.22);
    vec3 col = base;
    col += teal * fil * 0.60;
    col += mag * pow(fil, 1.5) * smoothstep(0.0, 0.6, n) * 0.85;
    col += amber * pow(fil, 4.0) * 0.55;
    col *= mix(1.0, 0.18, dust * cloud);
    return col * (0.28 + 1.05 * band);
}

vec3 hero(vec2 uv, vec4 h, vec3 tint){
    vec2 d = uv - h.xy;
    float r = length(d);
    float b = h.z, s = h.w;
    float core = exp(-r * r / (0.0012 * 0.0012 * (1.0 + 0.35 * b))) * 3.0;
    float halo = 0.0014 / (r + 0.0014) * 0.30 + exp(-r / 0.010) * 0.22 + exp(-r / 0.045) * 0.035;
    float L = 0.004 + 0.034 * s;
    vec2 ad = abs(d);
    float spk = exp(-ad.y / 0.0011) * exp(-ad.x / L) + exp(-ad.x / 0.0011) * exp(-ad.y / L);
    vec2 d2 = rot(0.785398) * d; vec2 ad2 = abs(d2);
    spk += 0.35 * (exp(-ad2.y / 0.0012) * exp(-ad2.x / (L * 0.45)) + exp(-ad2.x / 0.0012) * exp(-ad2.y / (L * 0.45)));
    // anamorphic horizontal streak
    float streak = exp(-ad.y / 0.0026) * exp(-ad.x / (L * 3.0)) * 0.22 * s;
    vec3 c = tint * (core + halo * 0.9) + mix(tint, vec3(0.7, 0.85, 1.0), 0.5) * (spk * 0.55 + streak);
    return c * b;
}

float hudMark(vec2 uv, vec2 c, float rev, out float arrow){
    float R = 0.034;
    vec2 d = uv - c;
    float r = length(d);
    float ang = atan(d.x, d.y) / TAU + 0.5;               // 0..1 clockwise from bottom
    float arcOn = step(ang, rev * 1.02);
    float ring = smoothstep(0.0012, 0.0, abs(r - R)) * arcOn;
    // ticks at cardinal points
    float tick = 0.0;
    for (int k = 0; k < 4; k++){
        float a = float(k) * PI * 0.5;
        vec2 dir = vec2(cos(a), sin(a));
        tick += smoothstep(0.0011, 0.0, sdSeg(uv, c + dir * (R + 0.004), c + dir * (R + 0.012)));
    }
    tick *= smoothstep(0.3, 0.7, rev);
    // leader: up-right then horizontal
    vec2 n = vec2(0.7071, 0.7071);
    vec2 a0 = c + n * (R + 0.003), a1 = c + n * (R + 0.050), a2 = a1 + vec2(0.130, 0.0);
    float lp = smoothstep(0.35, 1.0, rev);
    vec2 a1p = mix(a0, a1, clamp(lp * 2.0, 0.0, 1.0));
    vec2 a2p = mix(a1, a2, clamp(lp * 2.0 - 1.0, 0.0, 1.0));
    float ld = smoothstep(0.0010, 0.0, sdSeg(uv, a0, a1p));
    if (lp > 0.5) ld += smoothstep(0.0010, 0.0, sdSeg(uv, a1, a2p));
    arrow = ld;
    return ring + tick * 0.8;
}

void main(){
    vec2 frag = gl_FragCoord.xy;
    vec2 uv = (frag - 0.5 * uRes) / uRes.y;
    float t = uTime;

    // lensing warp near the light front
    vec2 duv = uv;
    float R = uRing.z;
    if (R > 0.012){
        vec2 dd = uv - uRing.xy;
        float r = length(dd);
        float w = exp(-pow((r - R) / (0.02 + 0.045 * R), 2.0));
        duv -= normalize(dd + 1e-5) * w * 0.022 * uRing.w * (0.5 + R);
    }

    float band;
    vec3 col = nebula(duv, t, band);
    float z = uZoom;
    col += starLayer(duv, 70.0, 1.0 + (z - 1.0) * 0.35, 1, 0.20, band) * 0.55;
    col += starLayer(duv, 34.0, 1.0 + (z - 1.0) * 0.7, 2, 0.11, band * 0.8) * 0.9;
    col += starLayer(duv, 15.0, 1.0 + (z - 1.0) * 1.3, 3, 0.055, band * 0.5) * 1.5;

    // hero stars + HUD
    float hudAcc = 0.0, leaderAcc = 0.0;
    for (int i = 0; i < 8; i++){
        if (i >= uNHero) break;
        vec4 h = uHero[i];
        // ring glint on hero
        float rd = abs(length(h.xy - uRing.xy) - uRing.z);
        float gl = (i == 0) ? 0.0 : exp(-rd * rd / (0.03 * 0.03)) * uRing.w * step(0.01, uRing.z);
        h.z *= (1.0 + 3.5 * gl); h.w = h.w + 0.9 * gl;
        vec3 tint = (i == 0) ? vec3(0.78, 0.87, 1.0) : mix(vec3(0.85, 0.9, 1.0), vec3(1.0, 0.86, 0.7), float(i % 3) * 0.4);
        col += hero(duv, h, tint);
        if (uHud[i] > 0.001){
            float ar;
            float m = hudMark(uv, h.xy, uHud[i], ar);
            hudAcc += m * uHudDim[i]; leaderAcc += ar * uHudDim[i];
        }
    }
    col += vec3(0.65, 0.82, 1.0) * (hudAcc * 0.55 + leaderAcc * 0.35);

    // the light front
    if (R > 0.004){
        vec2 dd = uv - uRing.xy;
        float r = length(dd);
        vec3 acc = vec3(0.0);
        for (int ch = 0; ch < 3; ch++){
            float Rc = R * (1.0 + (float(ch) - 1.0) * 0.006 * (0.4 + R));
            float e = abs(r - Rc);
            float w1 = 0.0013 + 0.0011 * R;
            float core = exp(-e * e / (w1 * w1));
            float glow = exp(-e / (0.018 + 0.05 * R)) * 0.30;
            float trail = (r < Rc) ? exp(-(Rc - r) / (0.10 + 0.22 * R)) * 0.20 : 0.0;
            acc[ch] = core * 3.4 + glow + trail;
        }
        // faint angular modulation so the front breathes
        float ang = atan(dd.y, dd.x);
        float mod_ = 0.82 + 0.18 * sin(ang * 5.0 + t * 0.8) * sin(ang * 3.0 - t * 0.5);
        col += acc * vec3(0.78, 0.9, 1.0) * uRing.w * mod_;
    }

    col *= uFadeIn;
    col += vec3(1.0, 0.95, 0.88) * uWhite;
    o = vec4(col, 1.0);
}
