#version 430
uniform sampler2D uTex;   // quarter-res bloom level
uniform vec2 uTexel;
out vec4 o;
void main(){
    vec2 uv = (floor(gl_FragCoord.xy) + 0.5) * uTexel;
    vec3 s = vec3(0.0); float ws = 0.0;
    for (int i = -32; i <= 32; i++){
        float w = exp(-abs(float(i)) * 0.085);
        s += textureLod(uTex, uv + vec2(float(i) * 2.0 * uTexel.x, 0.0), 0).rgb * w; ws += w;
    }
    o = vec4(s / ws, 1.0);
}
