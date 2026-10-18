#version 430
in float vD; in float vA; in float vC; in float vB; in float vSeed; in float vE; in float vSoft;
uniform float uFront;
uniform float uTime;
out vec4 o;
vec3 pcol(float c, float k){
    vec3 a = vec3(0.12, 0.95, 0.80), b = vec3(0.35, 0.65, 1.0), m = vec3(1.0, 0.35, 0.80);
    vec3 col = mix(a, b, smoothstep(0.0, 0.5, c));
    col = mix(col, m, smoothstep(0.45, 1.0, c));
    return mix(col, vec3(1.0), k);
}
void main(){
    vec2 q = (gl_PointCoord - 0.5) * 2.0;
    float d = length(q);
    if (d > 1.0) discard;
    float disc = smoothstep(1.0, 0.82, d);
    float gauss = exp(-d * d * 4.0);
    float shape = mix(gauss, disc * (0.55 + 0.45 * d), vSoft * 0.85);
    float sig = 0.0;
    float x = vD - uFront;
    if (vA > 0.0){
        float on = smoothstep(0.0, 0.25, -x + 0.12);     // lit once the front has reached it
        float flash = exp(-max(-x, 0.0) / 0.5) * on;       // x<0 : front passed
        float tail = exp(-max(-x, 0.0) / 2.6) * on;
        sig = (flash * 1.5 + tail * 0.28) * vA;
    }
    vec3 base = vec3(0.05, 0.28, 0.30) * vB * 0.5;
    vec3 col = base + pcol(vC, clamp(sig * 0.35, 0.0, 1.0)) * sig;
    o = vec4(col * shape * vE, 1.0);
}
