`timescale 1ns/1ps
module top_tb (
);

reg clk_tb;
logic rstn;
logic [13:0] a;
logic [13:0] b;
logic [28:0] c;
logic [7:0] num_frac_a;
logic [7:0] num_frac_b;
logic [7:0] num_frac_c;

parameter int period = 10;
parameter string data_path = "./simulation/";
parameter string in_data1 = {data_path,"input1.txt"};
parameter string in_data2 = {data_path,"input2.txt"};
parameter string out_data = {data_path,"output.txt"};


top top_inst (
    .clk(clk_tb),
    .rstn(rstn),
    .num_frac_a(num_frac_a),
    .num_frac_b(num_frac_b),
    .num_frac_c(num_frac_c),
    .a(a),
    .b(b),
    .c(c)
);

always #(period/2) clk_tb = ~clk_tb;

int input_file1,input_file2,output_file;
int input_data1, input_data2;
int start;

initial begin
    input_file1=$fopen(in_data1,"r");
    input_file2=$fopen(in_data2,"r");
  
    
    start = 0;
    rstn = 0;
    clk_tb = 1;
    #150
    rstn = 1;
    while (!$feof(input_file1) && !$feof(input_file2)) begin
        #(period)
	    start = 1;
        $fscanf(input_file1, "%d\n", input_data1);
        $fscanf(input_file2, "%d\n", input_data2);
        a = 14'(input_data1);
        b = 14'(input_data2);
        //$fwrite(output_file,"%d\n",c);
    end
    #(period*5)
    start = 1;
    $fclose(input_file1);
    $fclose(input_file2);
    $finish;
end

initial begin
    output_file=$fopen(out_data,"w");
    wait(start == 1);
    #(period*3.5)
    while(start == 1) begin
        #(period)
        $fwrite(output_file,"%d\n",c);
        
    end
    $fclose(output_file);
    $finish;
	
end

endmodule