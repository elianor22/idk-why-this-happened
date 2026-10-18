#version 430
in float vU; in float vD; in float vSoft; in float vFade; in float vA; in float vC; in float vB; in float vSeed;
uniform float uFront;
uniform float uTime;
uniform float uIdle;
out vec4 o;
vec3 pcol(float c, float k){
    // c: 0 sensory (cyan-mint) .. 1 brain (magenta-white)
    vec3 a = vec3(0.12, 0.95, 0.80), b = vec3(0.35, 0.65, 1.0), m = vec3(1.0, 0.35, 0.80);
    vec3 col = mix(a, b, smoothstep(0.0, 0.5, c));
    col = mix(col, m, smoothstep(0.45, 1.0, c));
    return mix(col, vec3(1.0), k);
}
void main(){
    float prof = exp(-vU * vU * mix(5.0, 1.5, vSoft));
    float sig = 0.0, core = 0.0;
    if (vA > 0.0){
        float x = vD - uFront;
        core = exp(-x * x / (0.32 * 0.32));
        float trail = (x < 0.0) ? exp(x / 1.6) : 0.0;
        float lead = exp(-max(x, 0.0) * 5.0) * 0.0;
        sig = (core * 3.0 + trail * 0.40) * vA;
    }
    // idle shimmer on everything
    float ph = fract(uTime * 0.11 + vSeed * 7.31);
    float idle = pow(max(sin(vD * 0.9 - uTime * 1.3 + vSeed * 40.0), 0.0), 6.0) * uIdle;
    vec3 base = vec3(0.03, 0.20, 0.24) * vB * 0.35;
    vec3 col = base * (0.35 + 0.65 * idle * 3.0) * 1.0;
    col += pcol(vC, clamp(core * 0.55, 0.0, 1.0)) * sig;
    o = vec4(col * prof * vFade, 1.0);
}
