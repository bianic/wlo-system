module control_unit #(
    parameter NUM_CHAN = 30
)(
    input clk,
    input rstn,
    // serial interface
    input              com_rxvalid,
    input  [7:0]       com_rxdata,
    output logic       com_txvalid,
    output logic [7:0] com_txdata,
    //mse result
    input  [63:0]      mse_data [1:0],
    input              mse_valid,
    // bit switch
    output logic [7:0] sw_int  [1:0][NUM_CHAN-1:0],
    output logic [7:0] sw_frac [1:0][NUM_CHAN-1:0],
    output logic       start,
    // system
    output logic       soft_rstn
);

//////////////////////////////////////////////////////////////// signals & param

// state machine
typedef enum logic [2:0] {
    IDLE = 3'b000,  // idle state
    FCTRL = 3'b001,  // set fraction switch
    ICTRL = 3'b010,  // set integer switch
    START = 3'b011,  // start emulation
    RESET = 3'b100,  // reset emulation
    RETRN = 3'b101   // return mse result to PC
} state_t;
state_t state, next_state;

// com interface register
logic       com_rxvalid_reg;
logic [7:0] com_rxdata_reg;

// mse result
logic [7:0] mse_data_reg [15:0];///////////////
logic [7:0] mse_byte_count;

// bit switch control register
logic [7:0] sw_int_gen  [2*NUM_CHAN-1:0];///////////////
logic [7:0] sw_frac_gen [2*NUM_CHAN-1:0];

// channel index
logic [7:0] chan_index;


integer i,j;
//////////////////////////////////////////////////////////////// logic

// com interface register
always @(posedge clk) begin
    if (!rstn) begin
        com_rxdata_reg  <= 0;
        com_rxvalid_reg <= 0;
        for (int i = 0; i < 8; i++) begin
            mse_data_reg[i] <= 0;
        end
    end 
    else begin
            com_rxdata_reg  <= com_rxdata;
            com_rxvalid_reg <= com_rxvalid;
        if (mse_valid) begin
            mse_data_reg[0] <= mse_data[0][7:0];
            mse_data_reg[1] <= mse_data[0][15:8];
            mse_data_reg[2] <= mse_data[0][23:16];
            mse_data_reg[3] <= mse_data[0][31:24];
            mse_data_reg[4] <= mse_data[0][39:32];
            mse_data_reg[5] <= mse_data[0][47:40];
            mse_data_reg[6] <= mse_data[0][55:48];
            mse_data_reg[7] <= mse_data[0][63:56];
            mse_data_reg[8] <= mse_data[1][7:0];
            mse_data_reg[9] <= mse_data[1][15:8];
            mse_data_reg[10] <= mse_data[1][23:16];
            mse_data_reg[11] <= mse_data[1][31:24];
            mse_data_reg[12] <= mse_data[1][39:32];
            mse_data_reg[13] <= mse_data[1][47:40];
            mse_data_reg[14] <= mse_data[1][55:48];
            mse_data_reg[15] <= mse_data[1][63:56];

        end
    end
end

// state machine  
always @(posedge clk) begin
    if (!rstn)
        state <= IDLE;
    else
        state <= next_state;
end
always @(state or com_rxvalid or com_rxdata or mse_valid or chan_index or mse_byte_count) begin
    case (state)
        IDLE: begin
            if (com_rxvalid && com_rxdata == 8'h01) begin
                next_state <= START;
            end
            else if (com_rxvalid && com_rxdata == 8'h02) begin
                next_state <= FCTRL;
            end
            else if (com_rxvalid && com_rxdata == 8'h03) begin
                next_state <= ICTRL;
            end
            else if (com_rxvalid && com_rxdata == 8'h04) begin
                next_state <= RESET;
            end
            else if (mse_valid) begin
                next_state <= RETRN;
            end
            else begin
                next_state <= IDLE;
            end
        end 
        FCTRL: begin
            if (chan_index == NUM_CHAN*2) begin////////////////////////
                next_state <= IDLE;
            end
            else begin
                next_state <= FCTRL;
            end
        end
        ICTRL: begin
            // unused, set to default
            next_state <= IDLE;
        end
        RESET: begin
            next_state <= IDLE;
        end
        START: begin
            next_state <= IDLE;
        end
        RETRN: begin
            if (mse_byte_count == 15) begin////////////////////////
                next_state <= IDLE;
            end
            else begin
                next_state <= RETRN;
            end
        end
        default:
                next_state <= IDLE;
    endcase
end
always @(state or sw_frac_gen or sw_int_gen or mse_data_reg or mse_byte_count) begin
    start      <= 0;
    soft_rstn  <= 1;
    // sw_frac    <= sw_frac_gen;
    // sw_int     <= sw_int_gen;

    com_txvalid <= 0;
    com_txdata  <= 0;

    for (i = 0; i < 2; i++) begin
        for (j = 0; j < NUM_CHAN; j++) begin
            sw_frac[i][j] <= sw_frac_gen[i*NUM_CHAN+j];
            sw_int[i][j]  <= sw_int_gen[i*NUM_CHAN+j];
        end
    end


    case (state)

        IDLE: begin
            //
        end
        FCTRL: begin
            //
        end
        ICTRL: begin
            //
        end
        START: begin
            start <= 1;
        end
        RESET: begin
            soft_rstn <= 0;
        end
        RETRN: begin
            com_txdata  <= mse_data_reg[mse_byte_count];
            com_txvalid <= 1;
        end
        default: begin
            //
        end
    endcase 
end
// channel index
always @(posedge clk) begin
    if (!rstn) begin
        chan_index <= 0;
    end
    else begin
        if (state == FCTRL || state == ICTRL) begin
            if (com_rxvalid == 1) begin
                chan_index <= chan_index + 1;
            end
        end
        else begin
            chan_index <= 0;
        end
    end
end

// bit switch control
always @(posedge clk) begin
    if (!rstn) begin
        for (int i = 0; i < NUM_CHAN*2; i++) begin//////
            sw_int_gen[i]  <= 8'h1E;
            sw_frac_gen[i] <= 8'h1E;
        end
    end
    else begin
        if (com_rxvalid == 1'b1) begin
            if (state == FCTRL) begin
                sw_frac_gen[chan_index] <= com_rxdata;
            end
            else if (state == ICTRL) begin
                sw_int_gen[chan_index]  <= com_rxdata;
            end
        end
    end
end

// mse byte count
always @(posedge clk) begin
    if (!rstn) begin
        mse_byte_count <= 0;
    end
    else begin
        if (state == RETRN) begin
            if (mse_byte_count < 16) begin///////////////////////
                mse_byte_count <= mse_byte_count + 1;
            end
            else begin
                mse_byte_count <= 0;
            end
        end
        else begin
            mse_byte_count <= 0;
        end
    end
end

endmodule
